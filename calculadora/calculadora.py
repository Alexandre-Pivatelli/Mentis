import soma, divide, multiplica, resto, subtrai


def main():
    num1 = float(input("Entre com o 1º número: "))
    num2 = float(input("Entre com o 2º número: "))
    oper = input("Entre com o operador: ")

    if oper == "+":
        print(soma.somaf(num1, num2))
    elif oper == "-":
        print(subtrai.subtraif(num1, num2))
    elif oper == "/":
        print(divide.dividef(num1, num2))
    elif oper == "%":
        print(resto.restof(num1, num2))
    elif oper == "*":
        print(multiplica.multiplicaf(num1, num2))


if __name__ == "__main__":
    main()
