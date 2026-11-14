from datetime import timedelta, timezone


def _texto(valor):
    valor = valor.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n')
    return valor.replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def _data_utc(valor):
    return valor.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _dobrar_linha(linha):
    # O limite é em bytes, mas a dobra deve preservar cada caractere UTF-8.
    partes = []
    trecho = ''
    tamanho = 0
    for caractere in linha:
        bytes_caractere = len(caractere.encode('utf-8'))
        if tamanho + bytes_caractere > 75:
            partes.append(trecho)
            trecho = ' '
            tamanho = 1
        trecho += caractere
        tamanho += bytes_caractere
    partes.append(trecho)
    return '\r\n'.join(partes)


def aula_ics(aula, gerado_em):
    inicio = aula.data_hora
    fim = inicio + timedelta(minutes=aula.duracao_min)
    linhas = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Mentis//Agenda de aulas//PT-BR',
        'BEGIN:VEVENT',
        f'UID:aula-{aula.pk}@mentis',
        f'DTSTAMP:{_data_utc(gerado_em)}',
        f'DTSTART:{_data_utc(inicio)}',
        f'DTEND:{_data_utc(fim)}',
        f'SUMMARY:{_texto(aula.disciplina.nome)}',
        f'LOCATION:{_texto(aula.local_ou_link)}',
        'STATUS:CONFIRMED',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    return '\r\n'.join(_dobrar_linha(linha) for linha in linhas) + '\r\n'
