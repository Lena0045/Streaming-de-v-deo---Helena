
# Devolutiva formativa — Atividade 02 da SA

**Estudante:** Helena Gonçalves Cordeiro  
**Turma:** Rio Negrinho — Manhã  
**Unidade Curricular:** Programação de Aplicativos  
**Projeto:** Streaming de Vídeo  
**Atividade:** Interface funcional  
**Arquivos analisados:** `interface/index.html`, `interface/style.css` e estrutura do código Python

## O que você já conseguiu desenvolver

Helena, você criou uma interface web relacionada ao seu projeto de streaming de vídeo.

O HTML apresenta componentes para gerenciamento de mídia, reprodução e atualização das informações do conteúdo.

Pontos positivos identificados:

- Criou uma página HTML estruturada com cabeçalho, seções e formulários.
- Utilizou templates Jinja2 para apresentar informações recebidas da aplicação.
- Incluiu mensagens de sucesso e erro.
- Criou formulário para adicionar vídeo MP4.
- Implementou campos para nome e descrição.
- Organizou ações de edição, substituição e exclusão de vídeo.
- Utilizou o elemento `video` e controles relacionados à reprodução.
- Aplicou atributos de validação HTML, como `required`, `maxlength` e `accept`.
- Incluiu comentários explicando diferentes partes do código.

## Comparação com a devolutiva anterior

### 1. Criação de interface — ATENDIDO

Na Atividade 01, foi recomendada a evolução do projeto para uma interface capaz de apresentar os recursos ao usuário.

Agora existe uma página com formulários e controles relacionados ao contexto de streaming.

**Evolução positiva:** a estrutura da interface está mais clara e organizada.

### 2. Testes de reprodução — PENDENTE DE COMPROVAÇÃO

A devolutiva anterior recomendou demonstrar a reprodução de mídia de ponta a ponta.

A nova página HTML apresenta componentes para isso, mas o funcionamento completo ainda não pôde ser confirmado pela inspeção dos arquivos.

### 3. Organização entre módulos — PARCIALMENTE ATENDIDO

O HTML está separado dos demais arquivos, mas é necessário restaurar ou identificar a implementação Python que atenderá às suas ações.

## O que precisa ser corrigido

### 4. Restaurar o arquivo Python responsável pelo sistema

Na versão atual do repositório, `codigo/dados_meu_streaming/app.py` está vazio.

O código Python anteriormente disponível foi retirado da estrutura atual.

**Como melhorar:** restaurar a versão funcional ou disponibilizar o arquivo que realmente executa o sistema. As ações de adicionar, editar, substituir e excluir precisam de rotas correspondentes.

### 5. Conferir a ligação entre HTML, Flask e CSS

O template utiliza referências como `/static/style.css`, enquanto o CSS disponível está em `interface/style.css`.

**Como melhorar:** configurar corretamente o diretório de arquivos estáticos no Flask ou ajustar o caminho utilizado no HTML.

### 6. Completar os estilos da interface

O arquivo CSS atual contém apenas regras básicas e não contempla vários componentes identificados no HTML.

**Como melhorar:** criar estilos correspondentes às classes utilizadas para cabeçalho, painéis, botões, avisos, formulários e reprodução.

## Oportunidades de melhoria

### 7. Validar o envio de vídeos também no servidor

O HTML limita a seleção a arquivos MP4, mas a validação no navegador não substitui a validação do backend.

**Como melhorar:** conferir no Python o tipo permitido, os limites do arquivo e as situações em que o envio não puder ser concluído.

### 8. Documentar as dependências

**Como melhorar:** atualizar o README com as bibliotecas necessárias, o procedimento de inicialização e a localização dos arquivos de mídia.

### 9. Testar ações de gerenciamento

**Como melhorar:** verificar se os formulários realmente executam as operações de adição, edição, substituição e exclusão, apresentando mensagens adequadas.

## Testes recomendados

1. Executar a aplicação pelo arquivo Python principal.
2. Verificar o carregamento do HTML e do CSS.
3. Adicionar um vídeo MP4 válido.
4. Tentar enviar um arquivo inadequado.
5. Reproduzir, pausar e retomar um vídeo.
6. Editar o nome e a descrição.
7. Substituir o vídeo por outro.
8. Cancelar e confirmar uma exclusão.
9. Reiniciar o sistema e verificar a disponibilidade do conteúdo.

## Prioridades para a próxima versão

1. **Restaurar e documentar o código Python executável.**
2. **Conectar as ações do HTML às rotas correspondentes.**
3. **Corrigir o carregamento do CSS.**
4. **Demonstrar a reprodução completa de vídeo.**
5. **Testar os formulários e as situações de erro.**

## Mensagem final

Helena, sua interface apresenta uma estrutura interessante para gerenciamento de conteúdo de vídeo.

Você avançou na apresentação das funcionalidades ao usuário e na documentação do HTML.

Agora é essencial garantir a ligação entre a interface e o código Python, demonstrando que os recursos apresentados realmente executam as operações previstas.
