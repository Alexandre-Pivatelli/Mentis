def restof(x, y):
    return x % y


def main():
    assert restof(3, 2) == 1, "Erro"
    assert restof(2.5, 2.5) == 0, "Erro"
    assert restof(3, 2) == 1, "Erro"
    assert restof(0, 5) == 0, "Erro"
    assert restof(5, 3) == 2, "Erro"
    assert restof(1.1, 1.1) == 0, "Erro"
    print("Todos os testes passaram com sucesso!")
    return


if __name__ == "__main__":
    main()
