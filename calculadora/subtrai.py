def subtraif(x, y):
    return x - y


def main():
    assert subtraif(3, 2) == 1, "Erro"
    assert subtraif(2.5, 2.5) == 0, "Erro"
    assert subtraif(-1.5, 4.5) == -6, "Erro"
    assert subtraif(0, 5) == -5, "Erro"
    assert subtraif(5, 0) == 5, "Erro"
    assert subtraif(1.1, 1.1) == 0, "Erro"
    print("Todos os testes passaram com sucesso!")
    return


if __name__ == "__main__":
    main()
