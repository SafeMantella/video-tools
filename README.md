# video-tools

**Camadas de vídeo locais (texto atrás do apresentador, tela verde, zoom, efeitos sonoros) e PDF de slides gerado de HTML.** Dois CLIs, sem API e sem custo por uso.

| ferramenta | o que faz | plataforma |
|---|---|---|
| [`video-camadas`](video-camadas) | separa o apresentador do fundo, remove tela verde, acha a zona livre acima da cabeça, compõe camadas (atrás / pessoa / frente), aplica zoom suave e sintetiza sfx | macOS (usa o Apple Vision) |
| [`slides-pdf`](slides-pdf) | HTML 16:9 → PDF (1 página por `.slide`) e **falha** se algum slide estoura a caixa | qualquer SO com Playwright |

## video-camadas

Uso típico: gravar falando pra câmera, e depois colocar um título **atrás** do corpo (efeito de profundidade), mover motion graphics só onde não cobre o rosto, dar zoom nos pontos de ênfase.

```bash
video-camadas pessoa  video.mp4 mascara.mkv            # silhueta da pessoa por frame (Apple Vision) -> vídeo cinza
video-camadas verde   video.mp4 mascara.mkv --cor auto # máscara por chroma key (cor 'auto' = cantos de cima do 1º frame)
video-camadas faces   video.mp4 rosto.json --cada 1    # caixa do rosto a cada N s e a zona livre (coords 1080x1920)
video-camadas camadas base.mp4 saida.mp4 --atras titulo.mov --mascara mascara.mkv --frente ui.mov \
                      [--slot ini:fim:arquivo] [--legenda legenda.mov] [--audio a.mp3]
video-camadas zoom    video.mp4 saida.mp4 --tabela "2:1.15:0.6,8:1.0:0.6"   # tempo:zoom:duração, suavizado
video-camadas sfx     eventos.json sfx.wav --dur 30         # cliques, whoosh, impact, riser, ding sintetizados
video-camadas self-check
```

- `camadas` empilha: base → atrás → **pessoa (pela máscara)** → frente → tela cheia → legenda (+ áudio).
- `sfx`: `eventos.json` é `[[tempo, "tipo", duração?], ...]` com tipos `main`, `soft`, `cut`, `whoosh`, `impact`, `riser`, `ding`. Sem arquivo de som externo.
- `faces` imprime o topo da cabeça mais alto e o queixo mais baixo, e daí a faixa do topo onde motion não cobre o rosto.
- `--w` define a largura de trabalho (padrão 960; a altura é 16:9 vertical). Trabalhe em 960 pra revisar e suba pra finalizar.

**Instalar:**

```bash
cd video-tools/video-camadas
python3 -m venv venv && ./venv/bin/pip install numpy pillow pyobjc-framework-Vision pyobjc-framework-Quartz
```

O wrapper `video-camadas` chama `venv/bin/python` desta pasta. Precisa de `ffmpeg` e `ffprobe` no PATH. `pessoa` e `faces` só funcionam no macOS; `verde`, `camadas`, `zoom` e `sfx` não dependem do Apple Vision.

## slides-pdf

Escreva os slides em HTML (cada slide um `<div class="slide" id="...">`, com `@page { size: 960pt 540pt; margin: 0 }`) e gere o PDF.

```bash
slides-pdf/slides-pdf deck.html                    # -> deck.pdf
slides-pdf/slides-pdf deck.html -o saida.pdf --png previas/   # + um PNG por slide
slides-pdf/set-logo deck.html nova-logo.png        # troca a logo (variável --logo no :root)
```

- Sai com erro se algum slide tem conteúdo estourando a caixa ou se o nº de páginas ≠ nº de slides. Isso evita descobrir o texto cortado só depois de mandar o PDF.
- Requer `pip install playwright && playwright install chromium`.
- Limites: precisa de internet na 1ª renderização (Google Fonts) e a checagem mede **altura**, não corte lateral.
- `kit/` guarda o logo e o favicon de exemplo (marca do autor, troque pelos seus).

## Antes de usar

Criado pro projeto de redes sociais do autor, no macOS. Há comentários e exemplos com caminhos do projeto (`ferramentas/…`, `gravações/…`); os scripts em si não dependem deles, mas ajuste o que apontar pra máquina do autor. Não há testes automatizados além do `video-camadas self-check`.

## Repos relacionados

Do kit do [@SafeMantella](https://github.com/SafeMantella): [video-cut-pipeline](https://github.com/SafeMantella/video-cut-pipeline) (corte antes das camadas), [transcrever-ptbr](https://github.com/SafeMantella/transcrever-ptbr) (legendas), [sau-tools](https://github.com/SafeMantella/sau-tools) (postar), [social-toolbox](https://github.com/SafeMantella/social-toolbox), [token-kit](https://github.com/SafeMantella/token-kit).

## Licença

MIT. Veja [LICENSE](LICENSE).
