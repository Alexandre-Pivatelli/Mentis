# __ENG4021 - Projeto de Software__
## Desenvolver um site relacionado a educação.
Integrantes: _Alexandre, Amanda Estevão, Beatriz Cunha, Beatriz Feijo, Pedro Cavalcante e Matheus Loureiro_

---

<p align="center">
  <img src="Site/MentisDjango/static/img/logo-r.png" alt="Logo do Mentis" width="220">
</p>

<h3 align="center">Mentis — Sua aula, do seu jeito</h3>

<p align="center">
  <img src="https://img.shields.io/badge/language-Python-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/framework-Django-green.svg" alt="Django">
  <img src="https://img.shields.io/badge/language-HTML-brown.svg" alt="HTML">
  <img src="https://img.shields.io/badge/language-CSS-red.svg" alt="CSS">
  <img src="https://img.shields.io/badge/Course-ENG4021-blue" alt="ENG4021">
  <img src="https://img.shields.io/badge/Institution-PUC--Rio-003366" alt="PUC-Rio">
</p>

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Telas](#telas)
- [Tecnologias](#tecnologias)
- [Como rodar o projeto](#como-rodar-o-projeto)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Equipe](#equipe)

## Sobre o projeto

O **Mentis** é uma plataforma que conecta estudantes do ensino fundamental e médio a professores particulares.

A ideia surgiu de um problema que apareceu na nossa pesquisa com estudantes: a maioria só conhece professores por indicação e aceita o preço cobrado por falta de opção. Ao mesmo tempo, muitos professores qualificados não têm um canal confiável para divulgar suas aulas e seus materiais.

No Mentis:

- o **estudante** encontra professores, compara preço, disciplina e avaliações, acessa materiais de estudo e acompanha suas aulas;
- o **professor** cria um perfil, publica materiais (PDFs, vídeos, links e listas de exercícios), informa seus horários disponíveis e recebe avaliações dos alunos.

> O objetivo principal é **democratizar o acesso à educação**, aproximando quem quer aprender de quem sabe ensinar.

## Funcionalidades

| Funcionalidade | O que faz |
|---|---|
| Página principal | Busca professores por nome ou disciplina e filtra por disciplina |
| Cadastro e login | Contas de **estudante** ou **professor**, com proteção contra excesso de tentativas |
| Perfil do professor | Biografia, formação, valor da hora-aula, materiais publicados, avaliações e horários |
| Ambiente do aluno | Resumo das aulas, agenda, disciplinas e avaliações feitas pelo aluno |
| Agenda e mensagens | O aluno acompanha suas aulas e conversa com os professores |
| Materiais | Lista dos materiais de estudo publicados pelos professores |
| Avaliações | Alunos avaliam as aulas e o próprio site |
| Editar perfil | Usuário altera seus dados e sua foto |
| Área administrativa | A equipe gestora vê e gerencia os usuários cadastrados |

## Telas

Algumas telas desenhadas no Figma antes da programação:

| Página principal | Login | Perfil do estudante |
|---|---|---|
| ![Página principal](documentos/Telas/Principal.png) | ![Login](documentos/Telas/Login.png) | ![Perfil do estudante](documentos/Telas/Perfil%20Estudante.png) |

## Tecnologias

- **Python** e **Django**: parte do servidor, banco de dados e páginas
- **SQLite**: banco de dados usado durante o desenvolvimento
- **HTML** e **CSS**: estrutura e visual das páginas
- **JavaScript**: interações simples nas páginas
- **Figma**: desenho das telas
- **GitHub** e **Codespaces**: versionamento e ambiente de desenvolvimento
- **Kanban** (GitHub Projects): organização das tarefas em sprints

## Como rodar o projeto

> [!TIP]
> O jeito mais fácil é usar o **GitHub Codespaces**: clique em **Code → Codespaces → Create codespace on main** e siga os passos abaixo no terminal.

1. Entre na pasta do site:

```bash
cd Site
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie as tabelas do banco de dados:

```bash
python manage.py migrate
```

4. (Opcional) Preencha o banco com dados fictícios para testar:

```bash
python manage.py popular_banco
python manage.py popular_professores
```

5. (Opcional) Crie um usuário administrador:

```bash
python manage.py createsuperuser
```

6. Inicie o servidor:

```bash
python manage.py runserver 0.0.0.0:8000
```

7. Abra o endereço que o Codespace mostrar para a porta **8000**.

> [!NOTE]
> Para rodar os testes automáticos, use `python manage.py test MentisDjango` dentro da pasta `Site`.

## Estrutura do repositório

```text
Mentis/
├── Site/                 → site principal em Django
│   ├── config/           → configurações do projeto (settings.py, urls.py)
│   ├── MentisDjango/     → aplicativo do Mentis
│   │   ├── models.py     → tabelas do banco de dados
│   │   ├── views*.py     → lógica de cada página
│   │   ├── templates/    → páginas HTML
│   │   ├── static/       → CSS, JavaScript e imagens
│   │   └── management/   → comandos para popular o banco
│   ├── manage.py
│   └── requirements.txt
├── documentos/           → pesquisas, escopo, requisitos, telas e análises
├── reuniões/             → atas das reuniões do grupo
├── calculadora/          → atividade inicial (Sprint 1)
└── core/ e mentis_project/ → primeira versão do banco de professores
```

## Equipe

| Integrante | GitHub |
|---|---|
| Alexandre Pivatelli | [@Alexandre-Pivatelli](https://github.com/Alexandre-Pivatelli) |
| Amanda Estevão | [@amandalcme](https://github.com/amandalcme) |
| Beatriz Cunha | [@BiaToledano](https://github.com/BiaToledano) |
| Beatriz Feijó | [@biafeijo](https://github.com/biafeijo) |
| Pedro Cavalcante | [@pedro-davii](https://github.com/pedro-davii) |
| Matheus Loureiro | [@llodzz](https://github.com/llodzz) |

---

<p align="center">Projeto desenvolvido para a disciplina <b>ENG4021 – Projeto Integrado de Software</b> — PUC-Rio, 2026.</p>
