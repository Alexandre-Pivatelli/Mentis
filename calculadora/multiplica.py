def multiplicaf(x, y):
    return x * y


def main():
    assert multiplicaf(3, 2) == 6, "Erro"
    assert multiplicaf(2.5, 2.5) == 6.25, "Erro"
    assert multiplicaf(-1, 4.5) == -4.5, "Erro"
    assert multiplicaf(0, 5) == 0, "Erro"
    assert multiplicaf(5, 0) == 0, "Erro"
    assert multiplicaf(1.1, 1) == 1.1, "Erro"
    print("Todos os testes passaram com sucesso!")
    return


if __name__ == "__main__":
    main()
