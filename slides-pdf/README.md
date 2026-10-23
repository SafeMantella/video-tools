# slides-pdf
HTML de slides -> PDF (1 página por `.slide`, 960x540pt). Chromium via Playwright (python3 do sistema).
`ferramentas/slides-pdf/slides-pdf deck.html [-o saida.pdf] [--png pasta]`
- Sai com erro se algum slide tem conteúdo estourando a caixa ou se nº de páginas != nº de slides.
- `--png pasta` salva um PNG por slide (o botão de controles aparece no PNG, não no PDF).
- Convenção do HTML: cada slide é `<div class="slide" id="...">`; `@page { size: 960pt 540pt; margin: 0 }`. Modelo: `gravações/long form/intro a IA/slides.html`.
- `set-logo deck.html nova-logo.png` troca a logo (vive em `--logo` no `:root`) e atualiza `kit/arfux-logo.png`.
- `kit/` guarda a logo do arfux.dev. Tokens, fontes e componentes em `memory/kit-visual-arfux-site-slides.md`.
- Limite: precisa de internet na 1ª renderização (Google Fonts). A checagem de estouro mede altura, não corte lateral.
