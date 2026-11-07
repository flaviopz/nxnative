# Fork flaviopz do nxnative: Zelda Ocarina of Time (Switch 2) no Mac

Este fork é o [nxnative](https://github.com/seedds/nxnative) com os ajustes feitos para jogar **The Legend of Zelda: Ocarina of Time** (Switch 2, `0400486024DEC000`, atualização v131072) num MacBook Air M4 de 16 GB. Os ajustes estão no ramo **`flaviopz-oot`**. O ramo `main` continua igual ao oficial.

**Este fork é focado em desempenho: o jogo roda travado em 30 fps**, no modo portátil, para ficar estável e liso num Mac de 16 GB. Não é uma versão de 60 fps.

Não há nenhum arquivo do jogo aqui. Você precisa do seu próprio dump do jogo (um arquivo `.nup` ou uma pasta com os arquivos dele).

## O que este fork tem a mais que o oficial

**Para o jogo rodar melhor**
- **Campo de Hyrule sem travar:** a GPU para bem menos para entregar leituras ao processador (copy-finalize e a tabela de escrita maior).
- **Burgo de Hyrule:** texturas que a GPU recria o tempo todo podem ser reaproveitadas (`DM_NVN_TAKEOVER_REUSE`). Esse ajuste ainda está em teste e fica desligado por padrão.
- **Tabela de memória dos shaders:** filtrada para conter só os endereços que os shaders usam. O resultado é menos memória presa.

**Para a imagem sair certa**
- **Folhagem:** grama e arbustos não balançam mais rápido demais. O tradutor de shaders apagava a coordenada que o shader do vento lê.
- **Pontinhos no upscaler:** sumiram as linhas pontilhadas em áreas lisas. As leituras de textura com deslocamento agora são escritas uma a uma.
- **Profundidade:** a profundidade dos shaders de pixel com várias saídas de cor é lida do registrador certo.
- **Upscaler do jogo:** consegue escrever direto numa imagem RGBA8, como no console.

**Botões do seu controle**
- O jogo mostra os botões de Xbox ou de PlayStation conforme o controle conectado, inclusive na tela de controles (veja "Botões de Xbox e PlayStation" abaixo).

**No jogo em si (perfil em `dm/games/0400486024DEC000`)**
- O jogo roda no ritmo certo quando o Mac faz 30 fps (frame step).
- A memória de modelos foi dobrada, porque ela enchia no Campo de Hyrule e o jogo fechava.
- Os vídeos usam o player simples, sem os 22 shaders do NDVE que travavam por 61 s.
- Os limites de memória foram medidos no Mac.

A cadeia de shaders deste ramo é a `b46c05d6f78f`. Ela foi conferida contra os shaders usados na partida: os mesmos bytes nos 60 shaders comparados.

## Como usar

Você precisa de um Mac com chip Apple e das mesmas ferramentas do nxnative oficial: Xcode, Homebrew, Python 3.12 ou mais novo e .NET. A lista completa está no [README](README.md#build-from-the-command-line).

**1. Instale as ferramentas** (uma vez só), no Terminal:

```
xcodebuild -downloadComponent MetalToolchain
brew install xcodegen zstd glslang
brew install --cask dotnet-sdk
python3 -m pip install lz4 "capstone>=5,<6" fonttools nsz zbic "backports.zstd; python_version < '3.14'" numpy pillow scipy shapely astc-encoder-py
```

**2. Baixe este fork já no ramo do Zelda:**

```
git clone -b flaviopz-oot https://github.com/flaviopz/nxnative.git
cd nxnative
```

Se você já tem o fork baixado, troque de ramo com `git fetch && git switch flaviopz-oot`.

**3. Monte o app do jogo** a partir do seu `.nup`:

```
python3 scripts/build_ipa_from_nsp.py ~/Games/ZeldaOoT/ZeldaOoT.nup --platform mac-app
```

Troque o caminho pelo do seu arquivo. A primeira montagem demora: os shaders são traduzidos do zero, e isso pode levar de 30 a 60 minutos. O app aparece na pasta do jogo e abre pelo Finder.

**4. Ajustes de memória: já vêm no app.** Desde 6 de novembro de 2026, a montagem coloca dentro do app as configurações que deixam o jogo estável num Mac de 16 GB. Elas ficam no arquivo `dm/games/0400486024DEC000/env.txt` do fork:

```
DM_NVN_POOL_BUDGET_MB=32
DM_NVN_GMEM_CHUNKS=1
DM_NVN_POOL_PER_FRAME=4
DM_NVN_UNC_ANY_POOL=1
DM_NVN_KEEP_SHARED_RETIRED=1
DM_FPS_TARGET=30
```

- `DM_NVN_POOL_BUDGET_MB=32` é a mais importante. Sem ela, ao entrar no jogo, o Mac tenta criar todas as texturas de uma vez, passa de 19 GB de memória de vídeo e a tela fica preta (às vezes o Mac até reinicia).
- As outras linhas `DM_NVN_*` são as configurações de memória que deixaram o Campo de Hyrule liso.
- `DM_FPS_TARGET=30` trava o jogo em 30 fps, com o ritmo certo. É a base do foco em desempenho deste fork, então não troque esse valor.

**Se você montou o app antes de 6 de novembro e teve tela preta:** baixe a versão nova do fork (`git pull`) e rode o passo 3 de novo. Se preferir não montar de novo, crie o arquivo `~/Library/Application Support/nxnative/0400486024DEC000/env.txt` com as linhas acima.

Modo portátil e idioma você escolhe na janela que aparece ao abrir o app. Se quiser deixar fixo, coloque no mesmo `env.txt` da sua pasta:

```
DM_OPMODE=0
DM_LANG=pt-BR
```

O `env.txt` da sua pasta (`~/Library/Application Support/nxnative/0400486024DEC000/`) é lido primeiro e vale por cima do que vem no app.
Feche e abra o app de novo depois de mudar o arquivo.

**Em teste, para o Burgo de Hyrule.** Estas duas linhas ainda não foram aprovadas jogando:

```
DM_NVN_TAKEOVER_REUSE=1
DM_NVN_BARRIER=game
```

Para desligar, apague as linhas.

`DM_NVN_POOL_PER_FRAME` acima de 5 não é seguro: as texturas podem ser liberadas cedo demais.

## Botões de Xbox e PlayStation

O jogo mostra os botões do controle que você conectar. Com um controle de **PlayStation** (DualSense ou DualShock 4), aparecem ○ ✕ △ □, L1/R1, L2/R2 e Options/Create. Com um controle de **Xbox**, aparecem B/A/Y/X, LB/RB, LT/RT e Menu/View. Com um Pro Controller, Joy-Con ou só o teclado, ficam os botões originais do jogo.

O que muda:
- os ícones nas falas e nos menus;
- as letras dos botões no HUD e os botões da ocarina;
- a tela **Controles básicos**, que passa a mostrar o desenho de um controle Xbox Series ou de um DualSense, com as linhas ligadas a cada botão, no modo portátil e na TV.

Os ícones seguem a posição do botão, porque o nxnative liga os controles de Xbox e PlayStation pela posição. O botão da direita é o "A" do jogo, então aparece como B no Xbox e como ○ no PlayStation.

Como funciona:
- A montagem do app (passo 3) cria as duas versões a partir do seu próprio jogo e coloca dentro do app. Para isso, o Python precisa dos pacotes `numpy pillow scipy shapely astc-encoder-py` do passo 1. Sem eles, a montagem avisa e o app sai só com os botões originais.
- Ao abrir o jogo, o app vê o fabricante do controle conectado (Sony, Microsoft ou Nintendo) e carrega a versão certa.
- Se você trocar de controle no meio da partida, os botões só mudam quando fechar e abrir o jogo de novo.

Para escolher manualmente, coloque uma destas linhas no `env.txt`:

```
DM_BOTOES=xbox
DM_BOTOES=ps
DM_BOTOES=nintendo
```

Os desenhos dos controles estão em `dm/games/0400486024DEC000/button_mods` (`xbox.png` e `ps5.png`), e o gerador fica na mesma pasta. Nenhum arquivo do jogo vai para o fork. Esse recurso ainda está em teste.

## Problemas conhecidos

- **Burgo de Hyrule e caminho até o castelo:** a taxa de quadros ainda cai.
- **Faixa branca na cerca do Rancho Lon Lon:** a causa ainda não foi encontrada.
- **Duas pipelines de folhagem** (task/mesh) ainda falham ao montar, então algumas plantas não aparecem.
- **Memória:** o jogo usa cerca de 14 GB num Mac de 16 GB, então feche outros apps pesados.
- **Tela preta ao entrar no jogo (Mac mini M4 e outros):** acontecia com apps montados sem os ajustes de memória. Corrigido em 6 de novembro de 2026: veja o passo 4.

## Apoie o fork

Se o fork te ajudou e você quiser apoiar as atualizações, dá para doar pelo PayPal: [doar pelo PayPal](https://www.paypal.com/donate/?hosted_button_id=CKZWQRPA2XAF2). Também dá para doar pelo botão **Sponsor** no topo da página do repositório.

## Atualizar a partir do oficial

Este ramo foi feito sobre o nxnative de 5 de novembro de 2026. O oficial também passou a ter um perfil do Ocarina of Time, então juntar os dois dá conflito em `dm/games/0400486024DEC000`. Mantenha o perfil deste ramo, se é o que você testou.
