# Como contribuir

Obrigado pelo interesse no Yuho Reader! Toda ajuda é bem-vinda: relatar um erro, sugerir uma melhoria,
corrigir um texto ou enviar código.

## Relatar um erro ou sugerir algo

Abra uma [issue](https://github.com/walterlijunior/yuho-reader/issues) contando:

- o que você fez (empresa, exercícios e tipos de relatório escolhidos);
- o que esperava e o que aconteceu;
- o trecho do **Registro** da página Downloads, se houver.

**Nunca publique a sua chave da API do EDINET** em issues, capturas de tela ou no código.

## Enviar código

1. Faça um *fork* do repositório e crie um ramo para a sua mudança.
2. Prepare o ambiente (Windows, Python 3.12):

   ```
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements-dev.txt
   ```

3. Faça a mudança. Algumas regras do projeto:
   - a lógica fica em `core/` e não importa nada de interface; as telas ficam em `ui/`, uma página por arquivo;
   - toda mudança em `core/` vem com teste em `tests/`, usando o EDINET simulado (`tests/fake_edinet.py`) —
     os testes não usam a internet nem uma chave de verdade;
   - cada arquivo `.py` novo começa com o mesmo aviso de licença dos demais;
   - textos da interface em português.
4. Rode os testes e confira que o programa abre:

   ```
   .venv\Scripts\python -m pytest
   .venv\Scripts\python run.py
   ```

5. Abra um *pull request* explicando o que mudou e por quê.

## Acordo de contribuição

Ao enviar uma contribuição, você confirma que ela é de sua autoria e concede a walterlijunior o direito de
usá-la, modificá-la e relicenciá-la, inclusive em versões comerciais do Yuho Reader, além de distribuí-la
sob a GPL-3.0.

## Licença

O Yuho Reader é distribuído sob a [GPL-3.0-or-later](LICENSE). O nome “Yuho Reader” não está incluído na
licença: versões modificadas devem usar outro nome.
