# Contribuindo

Obrigado por querer melhorar o heditor.

## Novo estilo
1. Produza pelo menos um vídeo com o estilo e passe por todos os gates de `references/quality-gates.md`.
2. Escreva `skills/heditor/references/styles/<slug>.md` seguindo `references/adding-styles.md` (mesma estrutura dos estilos existentes, em inglês, sem dados privados nem marcas de terceiros).
3. Adicione a linha em `references/styles/INDEX.md`, na tabela do `SKILL.md` e no `README.md`.
4. Se o estilo entrar na `description:` do frontmatter do `SKILL.md`, mantenha o valor entre aspas simples (texto com `: ` sem aspas quebra o YAML e o `npx skills` deixa de encontrar a skill). Um apóstrofo dentro do texto vira `''`. O CI lê o frontmatter com um parser YAML.

## Código do kit
- Python 3.10+, PEP 8, funções pequenas e determinísticas (nada de aleatoriedade sem semente).
- Rode `bash skills/heditor/scripts/setup.sh` e um corte completo (`heditor new` → `finalize`) antes de abrir o PR.
- Não adicione arquivos de áudio, vídeo ou fontes ao repositório: use o catálogo (`assets/catalog.json`) e o `fetch_assets.py`.

## Versões e releases
Toda alteração publicada no `main` sai como versão, com tag e release no GitHub.
1. Atualize `metadata.version` em `skills/heditor/SKILL.md` (semver: patch para correções e documentação, minor para estilos, comandos e recursos novos, major para mudanças incompatíveis).
2. Abra a seção `## X.Y.Z — AAAA-MM-DD` no topo do `CHANGELOG.md`.
3. Faça o commit com a mensagem `heditor X.Y.Z: <resumo>`, dê push no `main` e espere o CI passar nesse commit.
4. Crie a tag anotada e publique a release com as notas da seção do CHANGELOG:
   `git tag -a vX.Y.Z -m "heditor X.Y.Z: <resumo>" && git push origin vX.Y.Z`
   `gh release create vX.Y.Z --verify-tag --title "heditor X.Y.Z: <resumo>" --notes-file <notas.md> --latest`

## Issues
Descreva sistema operacional, agente usado, saída do `heditor doctor` e o comando que falhou.
