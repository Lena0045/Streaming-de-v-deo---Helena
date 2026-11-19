
# Devolutiva formativa — Atividade 01 da SA

**Estudante:** Helena Gonçalves Cordeiro  
**Turma:** Rio Negrinho — Manhã  
**Unidade Curricular:** Programação de Aplicativos  
**Projeto escolhido:** Streaming de vídeo  
**Referência:** Situação de Aprendizagem nº 1 — *Da Ideia ao Código*

## O que você já conseguiu desenvolver

Helena, seu projeto apresenta uma implementação extensa de uma aplicação relacionada a streaming de vídeo. Na análise anterior do código enviado, foram identificados recursos de programação orientada a objetos, funções auxiliares, validações e tratamento de exceções. Esses elementos demonstram preocupação com a organização do programa e com situações que podem ocorrer durante sua utilização.

Pontos positivos identificados:

- Utilizou **programação orientada a objetos**, organizando responsabilidades em classes e métodos.
- Aplicou **funções auxiliares** para dividir tarefas e reaproveitar partes da lógica.
- Incluiu **validações de dados e tratamento de exceções**, importantes para evitar que entradas ou operações inesperadas interrompam a aplicação sem explicação.
- Desenvolveu uma solução que envolve **ambiente gráfico e reprodução de mídia**, ampliando os conhecimentos trabalhados no código Python.
- Apresentou uma implementação de aproximadamente **918 linhas**, com diferentes componentes que precisam atuar de maneira integrada.
- Na revisão anterior, **as funções auxiliares verificadas apresentaram resultados adequados nos testes pontuais**.

## Pontos que precisam de atenção

### 1. Comprovar a reprodução de vídeo no ambiente de execução

A reprodução completa depende do ambiente gráfico e do VLC. Na verificação anterior, foi possível avaliar a estrutura do código e realizar testes pontuais de funções auxiliares, mas **a reprodução de mídia não foi confirmada de ponta a ponta**.

**Como melhorar:** executar o programa no computador de apresentação e demonstrar a seleção, o início e o encerramento de uma reprodução. Confirmar se o VLC e as bibliotecas necessárias estão instalados e se o programa encontra os arquivos ou endereços de mídia utilizados.

### 2. Documentar as dependências do projeto

Uma aplicação que depende de componentes gráficos e do VLC pode funcionar em um computador e apresentar dificuldades em outro, mesmo quando o código Python está correto.

**Como melhorar:** informar no README a versão de Python utilizada, as bibliotecas necessárias, a dependência do VLC, os comandos de instalação e o procedimento para iniciar a aplicação. Registrar também os formatos de mídia testados e eventuais limitações conhecidas.

### 3. Manter a organização de um código extenso

Um projeto com muitas linhas e diferentes funcionalidades exige atenção para que alterações em uma parte não prejudiquem as demais.

**Como melhorar:** verificar se interface, reprodução de mídia, validações e regras de funcionamento estão suficientemente separadas. Quando necessário, distribuir essas responsabilidades em módulos menores, com nomes claros e funções reutilizáveis.

## Oportunidades de melhoria

### 4. Ampliar os testes das situações de erro

As validações e exceções identificadas são positivas. O próximo passo é comprovar seu comportamento nos casos em que um recurso externo não está disponível.

**Como melhorar:** testar uma mídia inexistente, um caminho inválido, a ausência da biblioteca necessária e tentativas de executar operações fora da sequência esperada. Sempre que possível, apresentar uma mensagem compreensível e permitir que o programa continue ou encerre de forma controlada.

### 5. Separar testes de lógica dos testes de integração

Funções auxiliares podem funcionar corretamente isoladamente, mas isso não garante, por si só, que a reprodução e a interface estejam integradas.

**Como melhorar:** manter testes para funções que não dependem da interface e criar um roteiro manual para verificar o funcionamento completo da aplicação. Registrar quais resultados foram confirmados.

### 6. Aprimorar a documentação das responsabilidades

A orientação a objetos facilita a manutenção quando fica claro o papel de cada classe e método.

**Como melhorar:** utilizar docstrings curtas para explicar responsabilidades, parâmetros e resultados; manter comentários nos trechos de lógica mais complexa; e evitar explicações redundantes em operações simples.

### 7. Preparar a evolução do projeto

A estrutura inicial pode servir de base para novas funcionalidades, desde que o funcionamento essencial esteja demonstrado e seja possível reproduzir a execução em outro ambiente.

**Como melhorar:** priorizar uma versão estável, documentada e testável antes de ampliar os recursos. Nas etapas seguintes, integrar interface e armazenamento conforme os requisitos da Situação de Aprendizagem.

## Testes recomendados

1. Iniciar o programa em um ambiente com todas as dependências instaladas.
2. Demonstrar uma reprodução completa de mídia válida.
3. Verificar o comportamento ao informar um arquivo ou caminho inexistente.
4. Testar as operações de iniciar, interromper e encerrar a reprodução, conforme os controles disponíveis.
5. Verificar o comportamento quando uma dependência de reprodução não estiver disponível.
6. Executar novamente os testes das funções auxiliares após alterações no código.
7. Confirmar que a interface apresenta mensagens claras quando uma operação não puder ser concluída.
8. Seguir apenas as instruções do README para verificar se outra pessoa consegue executar o projeto.

## Prioridades para a próxima versão

1. **Demonstrar a reprodução de vídeo funcionando de ponta a ponta.**
2. **Documentar todas as dependências e o procedimento de execução.**
3. **Organizar as responsabilidades em classes e módulos de fácil manutenção.**
4. **Registrar testes de integração e situações de erro.**
5. **Manter a clareza da documentação e dos comentários.**

## Mensagem final

Helena, seu trabalho demonstra iniciativa para explorar **orientação a objetos, validações, tratamento de exceções e integração com recursos de reprodução de mídia**. A estrutura apresentada na análise anterior constitui uma base importante para a continuidade do projeto.

O próximo desafio é comprovar o funcionamento completo no ambiente de apresentação e tornar a instalação e os testes reproduzíveis. **Continue valorizando a organização do código e a verificação prática de cada funcionalidade.** Esses cuidados são essenciais para transformar uma implementação extensa em uma aplicação confiável e fácil de manter.
