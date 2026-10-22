def dividef(x, y):
    return x / y


def main():
    assert dividef(6, 2) == 3, "Erro"
    assert dividef(2.5, 2.5) == 1, "Erro"
    assert dividef(-3, 1.5) == -2, "Erro"
    assert dividef(0, 5) == 0, "Erro"
    assert dividef(5, 1) == 5, "Erro"
    assert dividef(1.1, 1.1) == 1, "Erro"
    print("Todos os testes passaram com sucesso!")
    return


if __name__ == "__main__":
    main()
