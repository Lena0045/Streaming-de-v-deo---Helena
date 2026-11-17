#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meu Streaming - sistema de reprodução e gerenciamento de UM único vídeo MP4.

Tecnologias: Python 3.9+, sqlite3, tkinter e python-vlc (requer o VLC instalado).

Estrutura criada automaticamente ao lado deste arquivo:
    dados_meu_streaming/
        streaming.db      -> banco SQLite
        videos/           -> arquivo MP4 cadastrado
"""

import os
import queue
import shutil
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import vlc
    VLC_ERRO = None
except Exception as exc:  # biblioteca ausente ou libVLC não encontrada
    vlc = None
    VLC_ERRO = f"{type(exc).__name__}: {exc}"

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------
TITULO = "Meu Streaming"
BASE_DIR = Path(__file__).resolve().parent / "dados_meu_streaming"
VIDEOS_DIR = BASE_DIR / "videos"
DB_PATH = BASE_DIR / "streaming.db"

TAMANHO_BLOCO = 4 * 1024 * 1024      # cópia em blocos de 4 MB (não carrega tudo na RAM)
SALTO_MS = 10_000                    # avançar/retroceder 10 segundos
LIMITE_NOME = 120
LIMITE_DESCRICAO = 1000
CAIXAS_INICIAIS_MP4 = (b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide")


class ErroValidacao(Exception):
    """Erro de validação com mensagem pronta para o usuário."""


# ----------------------------------------------------------------------------
# Funções utilitárias (sem interface gráfica)
# ----------------------------------------------------------------------------
def formatar_tamanho(numero_bytes):
    valor = float(numero_bytes)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            if unidade == "B":
                return f"{int(valor)} B"
            return f"{valor:.2f} {unidade}"
        valor /= 1024
    return f"{numero_bytes} B"


def formatar_tempo(milissegundos):
    if milissegundos is None or milissegundos < 0:
        milissegundos = 0
    total = int(milissegundos // 1000)
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segundos:02d}"
    return f"{minutos:02d}:{segundos:02d}"


def validar_arquivo_mp4(caminho):
    """Validação básica de um MP4 (existência, extensão, tamanho e cabeçalho).
    Retorna o tamanho em bytes ou levanta ErroValidacao."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroValidacao("O arquivo selecionado não existe.")
    if not caminho.is_file():
        raise ErroValidacao("O caminho selecionado não é um arquivo.")
    if caminho.suffix.lower() != ".mp4":
        raise ErroValidacao("Somente arquivos com extensão .mp4 são aceitos.")
    try:
        tamanho = caminho.stat().st_size
    except OSError as exc:
        raise ErroValidacao(f"Não foi possível ler o arquivo: {exc}")
    if tamanho <= 0:
        raise ErroValidacao("O arquivo está vazio.")
    try:
        with open(caminho, "rb") as f:
            cabecalho = f.read(12)
    except OSError as exc:
        raise ErroValidacao(f"Sem permissão ou falha ao abrir o arquivo: {exc}")
    if len(cabecalho) < 12 or cabecalho[4:8] not in CAIXAS_INICIAIS_MP4:
        raise ErroValidacao(
            "O arquivo não parece ser um MP4 válido (cabeçalho inesperado). "
            "Ele pode estar corrompido ou ter sido apenas renomeado para .mp4."
        )
    return tamanho


def resolver_caminho_video(relativo):
    """Converte o caminho salvo no banco em caminho absoluto, garantindo que
    ele esteja dentro da pasta de vídeos. Retorna None se for inválido."""
    try:
        completo = (BASE_DIR / relativo).resolve()
        completo.relative_to(VIDEOS_DIR.resolve())
    except (ValueError, OSError, TypeError):
        return None
    return completo


def remover_arquivo(caminho, tentativas=5):
    """Remove um arquivo com algumas tentativas (útil no Windows, onde o
    arquivo pode ficar bloqueado por instantes). Retorna True se removeu."""
    if caminho is None:
        return True
    for _ in range(max(1, tentativas)):
        try:
            Path(caminho).unlink(missing_ok=True)
            return True
        except OSError:
            time.sleep(0.2)
    return False


def validar_com_vlc(instancia, caminho, limite=8.0):
    """Analisa o arquivo com o libVLC. Retorna (ok, mensagem)."""
    media = None
    try:
        media = instancia.media_new(str(caminho))
        try:
            media.parse_with_options(vlc.MediaParseFlag.local, int(limite * 1000))
        except Exception:
            media.parse()
        falhou = getattr(getattr(vlc, "MediaParsedStatus", None), "failed", None)
        fim = time.monotonic() + limite
        duracao = media.get_duration()
        while (duracao is None or duracao <= 0) and time.monotonic() < fim:
            try:
                if falhou is not None and media.get_parsed_status() == falhou:
                    break
            except Exception:
                pass
            time.sleep(0.05)
            duracao = media.get_duration()
        if duracao is None or duracao <= 0:
            return False, ("O arquivo parece corrompido ou usa um formato/codec "
                           "incompatível: não foi possível ler a duração do vídeo.")
        try:
            faixas = list(media.tracks_get() or [])
            if faixas and not any(f.type == vlc.TrackType.video for f in faixas):
                return False, "O arquivo não contém uma trilha de vídeo."
        except Exception:
            pass
        return True, ""
    except Exception as exc:
        return False, f"Não foi possível analisar o arquivo: {exc}"
    finally:
        if media is not None:
            try:
                media.release()
            except Exception:
                pass


# ----------------------------------------------------------------------------
# Banco de dados
# ----------------------------------------------------------------------------
class Banco:
    """Acesso ao SQLite. A restrição CHECK (id = 1) garante, no próprio banco,
    que exista no máximo um vídeo cadastrado."""

    def __init__(self, caminho):
        self.con = sqlite3.connect(str(caminho))
        self.con.row_factory = sqlite3.Row
        with self.con:
            self.con.execute(
                """
                CREATE TABLE IF NOT EXISTS video (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    nome TEXT NOT NULL,
                    descricao TEXT NOT NULL DEFAULT '',
                    data_cadastro TEXT NOT NULL,
                    caminho TEXT NOT NULL,
                    tamanho INTEGER NOT NULL,
                    formato TEXT NOT NULL
                )
                """
            )

    def obter(self):
        linha = self.con.execute("SELECT * FROM video WHERE id = 1").fetchone()
        return dict(linha) if linha else None

    def salvar(self, nome, descricao, caminho_relativo, tamanho, formato):
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.con:  # transação: ou grava tudo ou nada
            self.con.execute(
                """
                INSERT OR REPLACE INTO video
                    (id, nome, descricao, data_cadastro, caminho, tamanho, formato)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                """,
                (nome, descricao, data, caminho_relativo, int(tamanho), formato),
            )
        return self.obter()

    def excluir(self):
        with self.con:
            self.con.execute("DELETE FROM video WHERE id = 1")

    def fechar(self):
        try:
            self.con.close()
        except sqlite3.Error:
            pass


# ----------------------------------------------------------------------------
# Janela de nome/descrição
# ----------------------------------------------------------------------------
class DialogoDados(tk.Toplevel):
    def __init__(self, pai, titulo, nome_inicial=""):
        super().__init__(pai)
        self.title(titulo)
        self.transient(pai)
        self.resizable(False, False)
        self.resultado = None

        quadro = ttk.Frame(self, padding=14)
        quadro.grid(row=0, column=0, sticky="nsew")

        ttk.Label(quadro, text="Nome do vídeo:").grid(row=0, column=0, sticky="w")
        self.var_nome = tk.StringVar(value=nome_inicial)
        self.entrada_nome = ttk.Entry(quadro, textvariable=self.var_nome, width=52)
        self.entrada_nome.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(quadro, text="Descrição (opcional):").grid(row=2, column=0, sticky="w")
        self.texto_desc = tk.Text(quadro, width=52, height=5, wrap="word")
        self.texto_desc.grid(row=3, column=0, sticky="ew", pady=(2, 10))

        botoes = ttk.Frame(quadro)
        botoes.grid(row=4, column=0, sticky="e")
        ttk.Button(botoes, text="Salvar", command=self._salvar).pack(side="left", padx=4)
        ttk.Button(botoes, text="Cancelar", command=self._cancelar).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.bind("<Escape>", lambda _e: self._cancelar())

        self.update_idletasks()
        try:
            x = pai.winfo_rootx() + (pai.winfo_width() - self.winfo_width()) // 2
            y = pai.winfo_rooty() + (pai.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:
            pass

        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.entrada_nome.focus_set()
        self.entrada_nome.selection_range(0, "end")
        self.wait_window(self)

    def _salvar(self):
        nome = self.var_nome.get().strip()
        descricao = self.texto_desc.get("1.0", "end").strip()
        if not nome:
            messagebox.showwarning(TITULO, "Informe o nome do vídeo.", parent=self)
            return
        if len(nome) > LIMITE_NOME:
            messagebox.showwarning(
                TITULO, f"O nome deve ter no máximo {LIMITE_NOME} caracteres.", parent=self)
            return
        if len(descricao) > LIMITE_DESCRICAO:
            messagebox.showwarning(
                TITULO, f"A descrição deve ter no máximo {LIMITE_DESCRICAO} caracteres.",
                parent=self)
            return
        self.resultado = (nome, descricao)
        self.destroy()

    def _cancelar(self):
        self.resultado = None
        self.destroy()


# ----------------------------------------------------------------------------
# Aplicação
# ----------------------------------------------------------------------------
class App:
    def __init__(self, root, banco):
        self.root = root
        self.banco = banco
        self.video = None
        self.ocupado = False
        self.tela_cheia = False
        self.vlc_instance = None
        self.player = None
        self._arrastando = False
        self._midia_carregada = False
        self._erro_mostrado = False

        root.title(TITULO)
        root.geometry("980x760")
        root.minsize(780, 620)

        self._criar_interface()
        self.root.update()
        self._iniciar_vlc()
        self._carregar_registro()

        root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        root.bind("<F11>", lambda _e: self.alternar_tela_cheia())
        root.bind("<Escape>", lambda _e: self._sair_tela_cheia())
        self.root.after(250, self._tick)

    # ------------------------------------------------------------------ UI
    def _criar_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.cabecalho = ttk.Label(self.root, text=TITULO, font=("TkDefaultFont", 22, "bold"))
        self.cabecalho.grid(row=0, column=0, pady=(10, 6))

        self.quadro_video = tk.Frame(self.root, bg="black")
        self.quadro_video.grid(row=1, column=0, sticky="nsew", padx=12)

        # controles de reprodução
        self.painel_controles = ttk.Frame(self.root)
        self.painel_controles.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 0))
        self.painel_controles.columnconfigure(1, weight=1)

        self.var_tempo_atual = tk.StringVar(value="00:00")
        self.var_tempo_total = tk.StringVar(value="00:00")
        ttk.Label(self.painel_controles, textvariable=self.var_tempo_atual, width=8).grid(row=0, column=0)
        self.slider = ttk.Scale(self.painel_controles, from_=0, to=1000, orient="horizontal")
        self.slider.grid(row=0, column=1, sticky="ew", padx=6)
        self.slider.bind("<ButtonPress-1>", self._pressionar_slider)
        self.slider.bind("<ButtonRelease-1>", self._soltar_slider)
        ttk.Label(self.painel_controles, textvariable=self.var_tempo_total, width=8).grid(row=0, column=2)

        linha = ttk.Frame(self.painel_controles)
        linha.grid(row=1, column=0, columnspan=3, pady=(6, 0))

        self.btn_reproduzir = ttk.Button(linha, text="Reproduzir", command=self.reproduzir)
        self.btn_pausar = ttk.Button(linha, text="Pausar", command=self.pausar)
        self.btn_continuar = ttk.Button(linha, text="Continuar", command=self.continuar)
        self.btn_retroceder = ttk.Button(linha, text="« 10s", command=lambda: self._saltar(-SALTO_MS))
        self.btn_avancar = ttk.Button(linha, text="10s »", command=lambda: self._saltar(SALTO_MS))
        self.btn_tela_cheia = ttk.Button(linha, text="Tela cheia", command=self.alternar_tela_cheia)

        self.botoes_player = [self.btn_reproduzir, self.btn_pausar, self.btn_continuar,
                              self.btn_retroceder, self.btn_avancar, self.btn_tela_cheia]
        for botao in (self.btn_reproduzir, self.btn_pausar, self.btn_continuar,
                      self.btn_retroceder, self.btn_avancar):
            botao.pack(side="left", padx=3)

        ttk.Label(linha, text="Volume:").pack(side="left", padx=(16, 4))
        self.var_volume_txt = tk.StringVar(value="80%")
        self.escala_volume = ttk.Scale(linha, from_=0, to=100, orient="horizontal",
                                       length=130, command=self._ao_mudar_volume)
        self.escala_volume.set(80)
        self.escala_volume.pack(side="left")
        ttk.Label(linha, textvariable=self.var_volume_txt, width=5).pack(side="left", padx=(4, 12))
        self.btn_tela_cheia.pack(side="left", padx=3)

        # gerenciamento
        self.painel_gerenciar = ttk.Frame(self.root)
        self.painel_gerenciar.grid(row=3, column=0, pady=10)
        self.btn_adicionar = ttk.Button(self.painel_gerenciar, text="Adicionar vídeo",
                                        command=lambda: self._iniciar_cadastro(False))
        self.btn_substituir = ttk.Button(self.painel_gerenciar, text="Substituir vídeo",
                                         command=lambda: self._iniciar_cadastro(True))
        self.btn_excluir = ttk.Button(self.painel_gerenciar, text="Excluir vídeo",
                                      command=self.excluir_video)
        for botao in (self.btn_adicionar, self.btn_substituir, self.btn_excluir):
            botao.pack(side="left", padx=6)

        # informações
        self.painel_info = ttk.LabelFrame(self.root, text="Informações do vídeo cadastrado", padding=8)
        self.painel_info.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.painel_info.columnconfigure(1, weight=1)
        self.info = {}
        campos = [("id", "ID:"), ("nome", "Nome:"), ("descricao", "Descrição:"),
                  ("data", "Cadastrado em:"), ("caminho", "Arquivo:"),
                  ("tamanho", "Tamanho:"), ("formato", "Formato:"), ("situacao", "Situação:")]
        for i, (chave, rotulo) in enumerate(campos):
            var = tk.StringVar(value="—")
            self.info[chave] = var
            ttk.Label(self.painel_info, text=rotulo, font=("TkDefaultFont", 9, "bold")).grid(
                row=i, column=0, sticky="nw", padx=(0, 8))
            ttk.Label(self.painel_info, textvariable=var, wraplength=760,
                      justify="left").grid(row=i, column=1, sticky="w")

        self.var_status = tk.StringVar(value="")
        self.rodape = ttk.Label(self.root, textvariable=self.var_status, anchor="w")
        self.rodape.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 6))

    # ------------------------------------------------------------ VLC
    def _iniciar_vlc(self):
        if vlc is None:
            self._mostrar_aviso_player(
                "Player indisponível.\n\n"
                "Instale o VLC e o pacote python-vlc (veja as instruções).\n"
                f"Detalhe: {VLC_ERRO}")
            return
        try:
            args = ["--quiet", "--no-video-title-show"]
            if sys.platform.startswith("linux"):
                args.append("--no-xlib")
            self.vlc_instance = vlc.Instance(*args)
            if self.vlc_instance is None:
                raise RuntimeError("não foi possível iniciar o libVLC")
            self.player = self.vlc_instance.media_player_new()
            identificador = self.quadro_video.winfo_id()
            if sys.platform.startswith("win"):
                self.player.set_hwnd(identificador)
            elif sys.platform == "darwin":
                self.player.set_nsobject(identificador)
            else:
                self.player.set_xwindow(identificador)
            self.player.video_set_mouse_input(False)
            self.player.video_set_key_input(False)
            self.player.audio_set_volume(int(float(self.escala_volume.get())))
        except Exception as exc:
            self.player = None
            self.vlc_instance = None
            self._mostrar_aviso_player(f"Não foi possível iniciar o player de vídeo.\n\nDetalhe: {exc}")

    def _mostrar_aviso_player(self, texto):
        tk.Label(self.quadro_video, text=texto, bg="black", fg="white",
                 justify="center", wraplength=600).place(relx=0.5, rely=0.5, anchor="center")

    # -------------------------------------------------------- Registro
    def _carregar_registro(self):
        try:
            self.video = self.banco.obter()
        except sqlite3.Error as exc:
            messagebox.showerror(TITULO, f"Falha ao ler o banco de dados:\n{exc}")
            self.video = None
        else:
            self._limpar_orfaos()
        self._atualizar_tudo()
        self._carregar_no_player()

    def _limpar_orfaos(self):
        """Remove sobras de operações interrompidas (arquivos video_* não referenciados)."""
        manter = None
        if self.video:
            caminho = resolver_caminho_video(self.video["caminho"])
            manter = caminho.name if caminho else None
        try:
            for item in VIDEOS_DIR.iterdir():
                if item.is_file() and item.name.startswith("video_") and item.name != manter:
                    remover_arquivo(item, tentativas=1)
        except OSError:
            pass

    def _caminho_video(self):
        if not self.video:
            return None
        return resolver_caminho_video(self.video["caminho"])

    def _arquivo_ok(self):
        caminho = self._caminho_video()
        return caminho is not None and caminho.is_file()

    def _atualizar_tudo(self):
        self._atualizar_info()
        self._atualizar_botoes()

    def _atualizar_info(self):
        v = self.video
        if not v:
            for var in self.info.values():
                var.set("—")
            self.info["situacao"].set("Nenhum vídeo cadastrado.")
            return
        caminho = self._caminho_video()
        try:
            data = datetime.strptime(v["data_cadastro"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
        except (ValueError, TypeError):
            data = str(v["data_cadastro"])
        self.info["id"].set(str(v["id"]))
        self.info["nome"].set(v["nome"])
        self.info["descricao"].set(v["descricao"] or "(sem descrição)")
        self.info["data"].set(data)
        self.info["caminho"].set(str(caminho) if caminho else "(caminho inválido)")
        self.info["tamanho"].set(f"{formatar_tamanho(v['tamanho'])} ({v['tamanho']} bytes)")
        self.info["formato"].set(str(v["formato"]).upper())
        if self._arquivo_ok():
            self.info["situacao"].set("Pronto para reproduzir.")
        else:
            self.info["situacao"].set(
                "ATENÇÃO: o arquivo de vídeo não foi encontrado. "
                "Use 'Substituir vídeo' ou 'Excluir vídeo'.")

    def _atualizar_botoes(self):
        tem = self.video is not None
        livre = not self.ocupado
        self.btn_adicionar.config(state="normal" if (livre and not tem) else "disabled")
        self.btn_substituir.config(state="normal" if (livre and tem) else "disabled")
        self.btn_excluir.config(state="normal" if (livre and tem) else "disabled")
        pode = livre and self.player is not None and tem and self._arquivo_ok()
        for botao in self.botoes_player:
            botao.config(state="normal" if pode else "disabled")
        self.slider.state(["!disabled"] if pode else ["disabled"])

    def _definir_ocupado(self, ocupado, texto=""):
        self.ocupado = ocupado
        self.var_status.set(texto)
        self._atualizar_botoes()

    # --------------------------------------------------------- Player
    def _carregar_no_player(self):
        self._parar_player(liberar_midia=True)
        if not self.player or not self._arquivo_ok():
            return
        try:
            media = self.vlc_instance.media_new(str(self._caminho_video()))
            self.player.set_media(media)
            media.release()
            self._midia_carregada = True
            self._erro_mostrado = False
        except Exception as exc:
            self._midia_carregada = False
            messagebox.showerror(TITULO, f"Não foi possível carregar o vídeo:\n{exc}")

    def _parar_player(self, liberar_midia=False):
        self._midia_carregada = False
        if self.player:
            try:
                self.player.stop()
            except Exception:
                pass
            if liberar_midia:
                try:
                    self.player.set_media(None)
                except Exception:
                    pass
        self._resetar_progresso()

    def _resetar_progresso(self):
        self.slider.set(0)
        self.var_tempo_atual.set("00:00")
        self.var_tempo_total.set("00:00")

    def _pode_reproduzir(self):
        if self.player is None:
            messagebox.showerror(TITULO, "O player de vídeo não está disponível. "
                                         "Verifique a instalação do VLC e do python-vlc.")
            return False
        if not self.video:
            messagebox.showinfo(TITULO, "Adicione um vídeo primeiro.")
            return False
        if not self._arquivo_ok() or not self._midia_carregada:
            messagebox.showerror(TITULO, "O arquivo de vídeo não está disponível.")
            return False
        return True

    def reproduzir(self):
        if not self._pode_reproduzir():
            return
        try:
            estado = self.player.get_state()
            if estado == vlc.State.Playing:
                return
            if estado == vlc.State.Paused:
                self.player.set_pause(0)
                return
            self.player.stop()
            self._erro_mostrado = False
            if self.player.play() == -1:
                messagebox.showerror(TITULO, "Não foi possível iniciar a reprodução.")
                return
            self.root.after(400, self._aplicar_volume)
        except Exception as exc:
            messagebox.showerror(TITULO, f"Erro ao reproduzir:\n{exc}")

    def pausar(self):
        if not self._pode_reproduzir():
            return
        try:
            if self.player.get_state() == vlc.State.Playing:
                self.player.set_pause(1)
        except Exception as exc:
            messagebox.showerror(TITULO, f"Erro ao pausar:\n{exc}")

    def continuar(self):
        if not self._pode_reproduzir():
            return
        try:
            if self.player.get_state() == vlc.State.Paused:
                self.player.set_pause(0)
        except Exception as exc:
            messagebox.showerror(TITULO, f"Erro ao continuar:\n{exc}")

    def _saltar(self, delta_ms):
        if not self._pode_reproduzir():
            return
        try:
            if self.player.get_state() not in (vlc.State.Playing, vlc.State.Paused):
                return
            duracao = self.player.get_length()
            atual = self.player.get_time()
            if duracao <= 0 or atual < 0:
                return
            novo = max(0, min(atual + delta_ms, max(duracao - 500, 0)))
            self.player.set_time(int(novo))
        except Exception as exc:
            messagebox.showerror(TITULO, f"Erro ao mover a reprodução:\n{exc}")

    def _ao_mudar_volume(self, valor):
        volume = int(float(valor))
        self.var_volume_txt.set(f"{volume}%")
        if self.player:
            try:
                self.player.audio_set_volume(volume)
            except Exception:
                pass

    def _aplicar_volume(self):
        if self.player:
            try:
                self.player.audio_set_volume(int(float(self.escala_volume.get())))
            except Exception:
                pass

    def _pressionar_slider(self, _evento):
        self._arrastando = True

    def _soltar_slider(self, _evento):
        self._arrastando = False
        if not self.player or not self._midia_carregada:
            return
        try:
            if self.player.get_state() not in (vlc.State.Playing, vlc.State.Paused):
                return
            duracao = self.player.get_length()
            if duracao <= 0:
                return
            posicao = min(float(self.slider.get()) / 1000.0, 0.999)
            self.player.set_time(int(duracao * posicao))
        except Exception:
            pass

    def _tick(self):
        try:
            self._atualizar_progresso()
        except Exception:
            pass
        self.root.after(250, self._tick)

    def _atualizar_progresso(self):
        if not self.player or not self._midia_carregada:
            return
        estado = self.player.get_state()
        if estado == vlc.State.Error:
            if not self._erro_mostrado:
                self._erro_mostrado = True
                self._parar_player()
                self._midia_carregada = True
                messagebox.showerror(
                    TITULO, "Falha na reprodução: o arquivo pode estar corrompido "
                            "ou usar um codec incompatível.")
            return
        if estado == vlc.State.Ended:
            self._resetar_progresso()
            return
        if estado in (vlc.State.Playing, vlc.State.Paused):
            duracao = self.player.get_length()
            atual = self.player.get_time()
            if duracao > 0:
                self.var_tempo_total.set(formatar_tempo(duracao))
                if not self._arrastando and atual >= 0:
                    self.slider.set(min(1000.0, atual * 1000.0 / duracao))
                    self.var_tempo_atual.set(formatar_tempo(atual))

    # ------------------------------------------------------ Tela cheia
    def alternar_tela_cheia(self):
        if self.video is None and not self.tela_cheia:
            return
        self.tela_cheia = not self.tela_cheia
        ocultaveis = (self.cabecalho, self.painel_gerenciar, self.painel_info, self.rodape)
        if self.tela_cheia:
            for widget in ocultaveis:
                widget.grid_remove()
            self.root.attributes("-fullscreen", True)
            self.btn_tela_cheia.config(text="Sair da tela cheia")
        else:
            self.root.attributes("-fullscreen", False)
            for widget in ocultaveis:
                widget.grid()
            self.btn_tela_cheia.config(text="Tela cheia")

    def _sair_tela_cheia(self):
        if self.tela_cheia:
            self.alternar_tela_cheia()

    # ------------------------------------------------ Adicionar/Substituir
    def _iniciar_cadastro(self, substituir):
        if self.ocupado:
            return
        if substituir and not self.video:
            messagebox.showinfo(TITULO, "Não há vídeo cadastrado para substituir.")
            return
        if not substituir and self.video:
            messagebox.showinfo(TITULO, "Já existe um vídeo cadastrado. Use 'Substituir vídeo'.")
            return

        titulo_janela = "Escolha o novo vídeo MP4" if substituir else "Escolha um vídeo MP4"
        selecionado = filedialog.askopenfilename(
            title=titulo_janela,
            filetypes=[("Vídeos MP4", "*.mp4 *.MP4"), ("Todos os arquivos", "*.*")])
        if not selecionado:
            return
        origem = Path(selecionado)

        try:
            tamanho = validar_arquivo_mp4(origem)
        except ErroValidacao as exc:
            messagebox.showerror(TITULO, str(exc))
            return

        atual = self._caminho_video()
        try:
            if atual is not None and atual.exists() and origem.resolve() == atual.resolve():
                messagebox.showinfo(TITULO, "Esse arquivo já é o vídeo cadastrado.")
                return
        except OSError:
            pass

        try:
            livre = shutil.disk_usage(VIDEOS_DIR).free
            if livre < tamanho + 50 * 1024 * 1024:
                messagebox.showerror(
                    TITULO, "Espaço em disco insuficiente para armazenar o vídeo.")
                return
        except OSError:
            pass

        dialogo = DialogoDados(self.root, "Substituir vídeo" if substituir else "Adicionar vídeo",
                               nome_inicial=origem.stem[:LIMITE_NOME])
        if dialogo.resultado is None:
            return
        nome, descricao = dialogo.resultado

        nome_arquivo = f"video_{uuid.uuid4().hex}.mp4"
        contexto = {
            "origem": origem,
            "destino": VIDEOS_DIR / nome_arquivo,
            "parcial": VIDEOS_DIR / (nome_arquivo + ".part"),
            "relativo": f"{VIDEOS_DIR.name}/{nome_arquivo}",
            "nome": nome,
            "descricao": descricao,
            "tamanho": tamanho,
            "progresso": {"copiado": 0},
            "fila": queue.Queue(),
        }
        self._definir_ocupado(True, "Copiando vídeo... 0%")
        threading.Thread(target=self._copiar_arquivo, args=(contexto,), daemon=True).start()
        self.root.after(100, self._acompanhar_copia, contexto)

    @staticmethod
    def _copiar_arquivo(ctx):
        """Executa em outra thread: copia em blocos para não travar a interface."""
        try:
            with open(ctx["origem"], "rb") as entrada, open(ctx["parcial"], "wb") as saida:
                while True:
                    bloco = entrada.read(TAMANHO_BLOCO)
                    if not bloco:
                        break
                    saida.write(bloco)
                    ctx["progresso"]["copiado"] += len(bloco)
                saida.flush()
                os.fsync(saida.fileno())
            ctx["fila"].put(("ok", None))
        except Exception as exc:
            ctx["fila"].put(("erro", exc))

    def _acompanhar_copia(self, ctx):
        try:
            tipo, erro = ctx["fila"].get_nowait()
        except queue.Empty:
            percentual = int(ctx["progresso"]["copiado"] * 100 / max(ctx["tamanho"], 1))
            self.var_status.set(f"Copiando vídeo... {min(percentual, 100)}%")
            self.root.after(100, self._acompanhar_copia, ctx)
            return
        if tipo == "erro":
            remover_arquivo(ctx["parcial"])
            self._definir_ocupado(False)
            messagebox.showerror(TITULO, f"Falha ao copiar o arquivo:\n{erro}")
            return
        self._finalizar_cadastro(ctx)

    def _finalizar_cadastro(self, ctx):
        destino, parcial = ctx["destino"], ctx["parcial"]
        self.var_status.set("Validando o vídeo...")
        self.root.update_idletasks()
        try:
            if parcial.stat().st_size != ctx["tamanho"]:
                raise ErroValidacao("A cópia ficou incompleta. Tente novamente.")
            os.replace(parcial, destino)
            if self.vlc_instance is not None:
                ok, mensagem = validar_com_vlc(self.vlc_instance, destino)
                if not ok:
                    raise ErroValidacao(mensagem)
        except Exception as exc:
            remover_arquivo(parcial)
            remover_arquivo(destino)
            self._definir_ocupado(False)
            messagebox.showerror(TITULO, f"O vídeo não foi cadastrado.\n\n{exc}")
            return

        antigo = self._caminho_video()
        self._parar_player(liberar_midia=True)  # libera o arquivo antigo
        try:
            novo = self.banco.salvar(ctx["nome"], ctx["descricao"], ctx["relativo"],
                                     ctx["tamanho"], "mp4")
        except sqlite3.Error as exc:
            remover_arquivo(destino)  # o vídeo antigo permanece intacto
            self._definir_ocupado(False)
            self._atualizar_tudo()
            self._carregar_no_player()
            messagebox.showerror(
                TITULO, f"Falha ao gravar no banco de dados. Nada foi alterado.\n\n{exc}")
            return

        self.video = novo
        aviso = ""
        if antigo is not None and antigo != destino:
            if not remover_arquivo(antigo):
                aviso = ("\n\nO arquivo do vídeo anterior não pôde ser apagado agora; "
                         "ele será removido na próxima abertura do programa.")
        self._definir_ocupado(False)
        self._atualizar_tudo()
        self._carregar_no_player()
        messagebox.showinfo(TITULO, "Vídeo cadastrado com sucesso." + aviso)

    # ------------------------------------------------------------ Excluir
    def excluir_video(self):
        if self.ocupado or not self.video:
            return
        if not messagebox.askyesno(
                TITULO,
                f"Excluir o vídeo \"{self.video['nome']}\"?\n\n"
                "O arquivo e o registro serão removidos permanentemente.",
                icon="warning", default="no"):
            return
        arquivo = self._caminho_video()
        self._sair_tela_cheia()
        self._parar_player(liberar_midia=True)
        try:
            self.banco.excluir()
        except sqlite3.Error as exc:
            messagebox.showerror(TITULO, f"Falha ao excluir o registro no banco:\n{exc}")
            self._carregar_no_player()
            return
        self.video = None
        aviso = ""
        if arquivo is not None and not remover_arquivo(arquivo):
            aviso = ("\n\nO arquivo não pôde ser apagado agora; "
                     "ele será removido na próxima abertura do programa.")
        self._atualizar_tudo()
        messagebox.showinfo(TITULO, "Vídeo excluído." + aviso)

    # ------------------------------------------------------------- Fechar
    def _ao_fechar(self):
        try:
            self._parar_player()
            if self.player:
                self.player.release()
            if self.vlc_instance:
                self.vlc_instance.release()
        except Exception:
            pass
        finally:
            self.banco.fechar()
            self.root.destroy()


# ----------------------------------------------------------------------------
# Inicialização
# ----------------------------------------------------------------------------
def main():
    root = tk.Tk()
    try:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        messagebox.showerror(TITULO, f"Não foi possível criar as pastas de dados:\n{exc}")
        root.destroy()
        return
    try:
        banco = Banco(DB_PATH)
        banco.obter()  # força a leitura para detectar banco corrompido
    except sqlite3.Error as exc:
        messagebox.showerror(
            TITULO,
            f"Não foi possível abrir o banco de dados:\n{DB_PATH}\n\n{exc}\n\n"
            "Se o arquivo estiver corrompido, renomeie-o e abra o programa novamente.")
        root.destroy()
        return
    App(root, banco)
    root.mainloop()


if __name__ == "__main__":
    main()