# GitHub Repo Stats

Gera estatísticas completas de um usuário dentro de um repositório GitHub, com coleta pela API oficial, exportação em JSON/CSV, gráficos em PNG e resumo em Markdown.

## Funcionalidades

- Consulta à API do GitHub com sessão HTTP, timeout, retries e tratamento de limite de requisições.
- Coleta dados gerais do repositório, linguagens, branches, tags, releases e contribuidores.
- Busca commits de um usuário em todas as branches e remove duplicados pelo SHA.
- Detalha commits, arquivos modificados, pull requests, issues e comentários.
- Coleta estatísticas oficiais do GitHub Insights: contributors, commit activity, code frequency, participation e punch card.
- Gera arquivos JSON, CSV, gráficos Matplotlib e `summary.md`.
- Cria automaticamente a pasta de resultados no formato `github_stats_<repo>_<usuario>_<timestamp>`.

## Tecnologias

- Python 3.10+
- requests
- pandas
- matplotlib
- python-dotenv
- pytest

## Estrutura

```text
github_repo_stats/
  api/                  Cliente da API do GitHub
  charts/               Geração de gráficos
  exceptions/           Exceções específicas
  exporters/            Exportadores CSV, JSON e Markdown
  models/               Dataclasses dos registros principais
  services/             Regras de coleta e consolidação
  utils/                Datas, arquivos, logs e texto
  config.py             Configuração por CLI, config.json e .env
  main.py               Coordenação da aplicação
tests/                  Testes automatizados sem chamadas reais à API
main.py                 Entrada para `python main.py`
```

## Instalação

```bash
git clone https://github.com/sayydaviid/Processamento-de-Imagens-API
cd Processamento-de-Imagens-API
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux e macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Token do GitHub

Para repositórios públicos, a aplicação pode executar sem token, mas o limite de requisições será menor. Para repositórios privados, o token precisa ter acesso ao repositório.

1. Entre no GitHub.
2. Acesse as configurações da conta.
3. Abra Developer settings.
4. Crie um Personal access token.
5. Selecione somente as permissões necessárias. Para repositórios públicos, use o menor conjunto possível de permissões. Para privados, conceda acesso ao repositório.
6. Copie o token.
7. Coloque o token no arquivo `.env`.
8. Nunca publique o arquivo `.env`.

Crie o `.env` a partir do exemplo:

Windows:

```bash
copy .env.example .env
```

Linux e macOS:

```bash
cp .env.example .env
```

Conteúdo esperado:

```env
GITHUB_TOKEN=cole_seu_token_aqui
GITHUB_API_VERSION=2022-11-28
```

O token é lido somente do `.env` ou das variáveis de ambiente. Ele não deve ser informado pela linha de comando e não é exportado nos relatórios.

você pode conseguir o token em:
https://github.com/settings/developers

Foto do perfil → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token

#### Configurações:
- Token name: repo-stats-processamento-imagens
- Expiration: 7 days ou 30 days
- Resource owner: sua conta
- Repository access: Only select repositories
- Repository: Disciplinas-gustavoresque-UFPA/Processamento-de-Imagens-2026v2

#### permissões:
- Metadata: Read-only
- Contents: Read-only
- Pull requests: Read-only
- Issues: Read-only

Depois clica em Generate token e copia.

## Configuração do repositório

Você pode executar com argumentos:

```bash
python main.py --owner Disciplinas-gustavoresque-UFPA --repo Processamento-de-Imagens-2026v2 --user sayydaviid
```

Ou usar um arquivo JSON:

```bash
copy config.example.json config.json
```

Linux e macOS:

```bash
cp config.example.json config.json
```

Exemplo de `config.json`:

```json
{
  "owner": "Disciplinas-gustavoresque-UFPA",
  "repository": "Processamento-de-Imagens-2026v2",
  "username": "sayydaviid"
}
```

Execute:

```bash
python main.py --config config.json
```

A prioridade é: argumentos do terminal, depois `config.json`. Se faltarem dados obrigatórios, a aplicação mostra uma mensagem clara.

## Arquivos gerados

- `summary.json`: resumo consolidado do repositório, usuário e links úteis.
- `summary.md`: resumo em Markdown para relatório.
- `json/*.json`: respostas brutas ou consolidadas da API.
- `csv/my_commits.csv`: commits do usuário.
- `csv/my_commit_files.csv`: arquivos alterados por commit.
- `csv/my_commits_by_day.csv`: commits por dia.
- `csv/my_commits_by_week.csv`: commits por semana.
- `csv/my_file_churn.csv`: arquivos mais alterados.
- `csv/contributors.csv`, `csv/languages.csv`, `csv/branches.csv`, `csv/tags.csv`, `csv/releases.csv`.
- `csv/my_pull_requests.csv`, `csv/my_issues.csv`, `csv/my_issue_comments.csv`, `csv/my_pr_review_comments.csv`.
- `csv/repo_stats_*.csv`: estatísticas oficiais do GitHub Insights.
- `charts/*.png`: gráficos em resolução adequada.
- `application.log`: log da execução dentro da pasta de saída.

## Gráficos

A aplicação gera os mesmos gráficos do script original:

- `commits_por_dia.png`
- `adicoes_remocoes_por_dia.png`
- `arquivos_mais_alterados.png`
- `linguagens_repositorio.png`

Quando não existem dados para um gráfico, a aplicação registra a situação em log e continua a execução.

## Erros comuns

- `GITHUB_TOKEN não está configurado`: configure o `.env` ou execute apenas em repositórios públicos aceitando o limite menor.
- `Limite de requisições atingido`: aguarde o horário indicado ou use um token válido.
- `Recurso não encontrado`: confira owner, repository e permissões do token.
- `Arquivo de configuração inválido`: valide o JSON do `config.json`.
- Estatísticas com HTTP 202: o GitHub ainda está calculando o Insights; a aplicação tenta novamente automaticamente.

## Segurança

- Não coloque token em arquivos Python.
- Não publique `.env`.
- Use permissões mínimas no token.
- Revogue tokens que tenham sido expostos.
- Não compartilhe logs se eles contiverem nomes de repositórios privados ou informações sensíveis do projeto.

## Testes

Os testes usam mocks e não fazem chamadas reais à API do GitHub:

```bash
pytest
```

## Compatibilidade

O projeto usa `pathlib`, UTF-8 e caminhos relativos, funcionando em Windows, Linux e macOS com Python 3.10 ou superior.

## Como contribuir

1. Crie uma branch.
2. Faça alterações pequenas e focadas.
3. Execute `pytest`.
4. Abra um pull request explicando a motivação, o impacto e os testes executados.

## Licença

Distribuído sob a licença MIT. Consulte `LICENSE`.

## Limitações conhecidas

- A API do GitHub pode atrasar estatísticas do Insights e retornar HTTP 202.
- Repositórios muito grandes podem exigir muitas requisições e atingir rate limit.
- Comentários em conversas de PR e comentários de revisão são endpoints diferentes; a aplicação preserva os endpoints usados pelo script original.
- Commits são buscados por autor em cada branch; commits com metadados de autor divergentes do login podem não aparecer no filtro da API.
