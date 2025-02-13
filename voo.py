#!/usr/bin/env python3
import json
import requests
from config.config import API_KEY, SPREADSHEET_ID
from datetime import datetime, date

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


CITY_TO_AIRPORTS = {
    # Brasil
    "sao paulo": "GRU,CGH",
    "são paulo": "GRU,CGH",
    "sp": "GRU,CGH",
    "rio de janeiro": "GIG,SDU",
    "rj": "GIG,SDU",
    "brasilia": "BSB",
    "brasília": "BSB",
    "belo horizonte": "CNF,PLU",
    "bh": "CNF,PLU",
    "salvador": "SSA",
    "recife": "REC",
    "fortaleza": "FOR",
    "curitiba": "CWB",
    "porto alegre": "POA",
    "manaus": "MAO",
    "belém": "BEL",
    "belem": "BEL",

    # Estados Unidos
    "new york": "JFK,LGA,EWR",
    "ny": "JFK,LGA,EWR",
    "los angeles": "LAX,BUR",
    "la": "LAX,BUR",
    "chicago": "ORD,MDW",
    "miami": "MIA,FLL",
    "dallas": "DFW,DAL",
    "houston": "IAH,HOU",
    "washington": "IAD,DCA,BWI",
    "dc": "IAD,DCA,BWI",
    "san francisco": "SFO,OAK,SJC",
    "sf": "SFO,OAK,SJC",
    "las vegas": "LAS",
    "orlando": "MCO",
    "seattle": "SEA",
    "boston": "BOS",
    "atlanta": "ATL",

    # China
    "beijing": "PEK,PKX",
    "pequim": "PEK,PKX",
    "shanghai": "PVG,SHA",
    "xangai": "PVG,SHA",
    "guangzhou": "CAN",
    "cantao": "CAN",
    "shenzhen": "SZX",
    "chengdu": "CTU",
    "hangzhou": "HGH",
    "xiamen": "XMN",
    "nanjing": "NKG",
    "chongqing": "CKG",
    "wuhan": "WUH",
    "hong kong": "HKG",
    "macau": "MFM"
}

AIRPORTS_BY_COUNTRY = {
    'BRAZIL': [
        'GRU', 'CGH', 'GIG', 'SDU', 'BSB', 'CNF', 'PLU', 'SSA',
        'REC', 'FOR', 'CWB', 'POA', 'MAO', 'BEL'
    ],
    'USA': [
        'JFK', 'LGA', 'EWR', 'LAX', 'BUR', 'ORD', 'MDW', 'MIA',
        'FLL', 'DFW', 'DAL', 'IAH', 'HOU', 'IAD', 'DCA', 'BWI',
        'SFO', 'OAK', 'SJC', 'LAS', 'MCO', 'SEA', 'BOS', 'ATL'
    ],
    'CHINA': [
        'PEK', 'PKX', 'PVG', 'SHA', 'CAN', 'SZX', 'CTU', 'HGH',
        'XMN', 'NKG', 'CKG', 'WUH', 'HKG', 'MFM'
    ]
}


def format_time(time_str):
    """Formata o horário para um formato mais legível."""
    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    return dt.strftime('%d/%m/%Y %H:%M')


def print_medium_ticket_price(historic_price_data, price_data):
    """Funcao para calcular preco medio da passagem, priorizando o maior valor
    seja historico ou atual, dado que esse codigo é feito para uma planilha
    de orçamento """
    historical_medium_price = (historic_price_data["typical_price_range"][0] + historic_price_data["typical_price_range"][1])/2
    if price_data > historical_medium_price:
        medium_price = price_data
    else:
        medium_price = historical_medium_price

    return medium_price


def print_flight_info(flight_data):
    """Imprime informações do voo formatadas."""
    print("\n" + "="*50)

    for item in flight_data:
        print("\n📋 DETALHES DO ITINERÁRIO")
        print("-"*30)

        for flight in item["flights"]:
            print("\n✈️  Trecho do Voo:")
            print(f"   Partida: {flight['departure_airport']['name']}")
            print(f"   Horário: {format_time(flight['departure_airport']['time'])}")
            print(f"\n   Chegada: {flight['arrival_airport']['name']}")
            print(f"   Horário: {format_time(flight['arrival_airport']['time'])}")
            print(f"\n   Companhia: {flight['airline']}")
            print(f"   Aeronave: {flight['airplane']}")

        print(f"\n💰 Preço: R$ {item['price']:.2f}")
        print("-"*50)


def get_country_from_airport(airport_code):
    """Retorna o país do aeroporto com base no código."""
    for country, airports in AIRPORTS_BY_COUNTRY.items():
        if airport_code in airports:
            return country
    return None


def is_international_flight(departure_airports, arrival_airports):
    """Verifica se é um voo internacional comparando países de origem e destino."""
    # Separa os códigos de aeroporto
    dep_codes = departure_airports.split(',')
    arr_codes = arrival_airports.split(',')

    # Pega o país do primeiro aeroporto de origem
    departure_country = None
    for dep_code in dep_codes:
        departure_country = get_country_from_airport(dep_code)
        if departure_country:
            break

    # Pega o país do primeiro aeroporto de destino
    arrival_country = None
    for arr_code in arr_codes:
        arrival_country = get_country_from_airport(arr_code)
        if arrival_country:
            break

    # Se não conseguiu identificar algum dos países, assume internacional por segurança
    if not departure_country or not arrival_country:
        return True

    # É internacional se os países forem diferentes
    return departure_country != arrival_country


def search_flights(cidade_departure, cidade_arrival, outbound_date, return_date):
    """Realiza a busca de voos usando a SerpAPI."""
    departure = CITY_TO_AIRPORTS.get(cidade_departure.lower(), "")
    arrival = CITY_TO_AIRPORTS.get(cidade_arrival.lower(), "")

    # Verifica se é voo internacional (simplificado)
    is_international = is_international_flight(departure, arrival)

    # Identifica o país de destino para ajustes específicos
    dest_country = None
    for arr_code in arrival.split(','):
        dest_country = get_country_from_airport(arr_code)
        if dest_country:
            break

    params = {
        "api_key": API_KEY,
        "engine": "google_flights",
        "departure_id": departure,
        "arrival_id": arrival,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "BRL",
        "hl": "pt-BR"
    }

    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        data = response.json()

        if "error" in data:
            print(f"Erro na API: {data['error']}")
            return None

        flight_data = None
        for key in ["best_flights", "other_flights", "flights"]:
            if key in data:
                flight_data = data[key]
                break

        if flight_data:
            print_flight_info(flight_data)

            precos = []
            for item in flight_data:
                if 'price' in item and item['price'] not in precos:
                    precos.append(item['price'])

        if precos:
            preco_medio = sum(precos) / len(precos)

            # Ajuste para voos internacionais com base no destino
            if is_international:
                if "price_insights" in data:
                    historical_price = print_medium_ticket_price(data["price_insights"], preco_medio)
                    # Ajuste baseado no país de destino com valores mais realistas
                    adjustment_factor = 2.0  # fator padrão para internacional
                    if dest_country == 'CHINA':
                        adjustment_factor = 4.0  # Ajuste maior para China
                        # Define um preço mínimo para China
                        preco_minimo = 15000  # Preço mínimo para voos para China
                    elif dest_country == 'USA':
                        adjustment_factor = 1  # Ajuste para EUA
                        preco_minimo = 3500  # Preço mínimo para voos para EUA
                    else:
                        preco_minimo = 3000  # Preço mínimo para outros voos internacionais

                    preco_medio = max(preco_medio, historical_price) * adjustment_factor
                    # Garante que o preço não fique abaixo do mínimo estabelecido
                    preco_medio = max(preco_medio, preco_minimo)
                else:
                    # Se não houver dados históricos, aplica um ajuste ainda maior
                    if dest_country == 'CHINA':
                        preco_medio = max(preco_medio * 5.0, 15000)  # Garante mínimo de 15000
                    elif dest_country == 'USA':
                        preco_medio = max(preco_medio, 3500)   # Garante mínimo de 5000
                    else:
                        preco_medio = max(preco_medio * 2.5, 3000)   # Garante mínimo de 4000
            else:
                preco_medio *= 1.3

            print(f"\nPreço médio dos voos: R$ {preco_medio:.2f}")

            if "price_insights" in data:
                return max(print_medium_ticket_price(data["price_insights"],preco_medio), preco_medio)
            return preco_medio

            print("Não foi possível calcular o preço médio")
            return None

        print("Nenhum voo encontrado para esta rota e data.")
        return None

    except Exception as e:
        print(f"Erro inesperado: {e}")
        return None


def verify_format(date: str) -> bool:
    """Funcao para verificar se o formato da data esta correto."""
    if len(date) != 10:
        print("Estrutura incorreta, tem que ser YYYY-MM-DD")
        return False

    # Para verificar se o formato esta correto
    if date[4] != '-' or date[7] != '-':
        print("Estrutura incorreta, tem que ser YYYY-MM-DD")
        return False

    year = ""
    month = ""
    day = ""
    # Para verificar so tem digitos escritos e atribuir data para as variaveis y, m, d para assim verificar se a data é possivel
    for i in range(10):
        if i == 4 or i == 7:
            continue
        if i < 4:
            year += date[i]
        elif i < 7:
            month += date[i]
        elif i < 10:
            day += date[i]
        if not date[i].isdigit():
            print("Digite apenas números na data")
            return False

    # Converte o string em int e envia para verify date para verificar a data
    year_int = int(year)
    day_int = int(day)
    month_int = int(month)

    return verify_date(year_int, month_int, day_int)


def verify_date(year: int, month: int, day: int) -> bool:
    """Funcao para verificar se a data é possivel."""
    date_today = date.today()

    if day > 31:
        print("Dia não existe")
        return False
    if month > 12:
        print("Mes não existe")
        return False

    if date_today.year > year:
        print("O ano não pode ser no passado")
        return False

    if date_today.month > month and date_today.year == year:
        print("O mes não pode ser no passado")
        return False

    if date_today.day > day and date_today.month == month and date_today.year == year:
        print("O dia não pode ser no passado")
        return False

    return True


# integração com google sheets api
def setup_google_sheets():
    """Configura e retorna o serviço do Google Sheets."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = 'config/credentials.json'  # Substitua pelo caminho do seu arquivo de credenciais

    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=credentials)
    return service


def process_sheet_data(spreadsheet_id):
    """Funcao para processar os dados do google sheets."""
    service = setup_google_sheets()
    sheet = service.spreadsheets()

    # Define um range específico
    range_input = 'Página1!A1:D100'

    try:
        # Primeiro tenta ler os dados
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_input
        ).execute()

        values = result.get('values', [])
        if not values:
            print('Nenhum dado encontrado na planilha.')
            return

        # Pula o cabeçalho
        header = values[0]
        rows = values[1:]

        # Lista para armazenar os preços médios
        precos_medios = []

        # Processa cada linha
        for row in rows:
            if len(row) < 4:  # Verifica se tem todas as colunas necessárias
                precos_medios.append(['Dados incompletos'])
                continue

            cidade_departure = row[0]
            cidade_arrival = row[1]
            date_outbound = row[2]
            date_return = row[3]

            # Verifica o formato das datas
            if not (verify_format(date_outbound) and verify_format(date_return)):
                precos_medios.append(['Formato de data inválido'])
                continue

            try:
                # Busca os voos e calcula o preço médio
                response = search_flights(
                    cidade_departure,
                    cidade_arrival,
                    date_outbound,
                    date_return
                )

                # Adiciona o preço médio à lista
                if response:
                    precos_medios.append([response])
                else:
                    precos_medios.append(['Não encontrado'])

            except Exception as e:
                precos_medios.append([f'Erro: {str(e)}'])

        # Prepara o body no formato correto
        myBody = {
            'range': f'Página1!E2:E{len(rows)+1}',
            'values': precos_medios,
            'majorDimension': 'ROWS'
        }

        # Atualiza a planilha
        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=f'Página1!E2:E{len(rows)+1}',
            valueInputOption='RAW',
            body=myBody
        ).execute()

        print(f'Preços atualizados para {len(rows)} voos.')

    except Exception as e:
        print(f'Erro ao processar planilha: {str(e)}')


def test_sheet_access(spreadsheet_id):
    service = setup_google_sheets()
    sheet = service.spreadsheets()

    try:
        # Primeiro vamos tentar obter informações sobre a planilha
        spreadsheet = sheet.get(spreadsheetId=spreadsheet_id).execute()

        # Imprime informações sobre todas as abas
        print("\nInformações da planilha:")
        for sheet in spreadsheet.get('sheets', []):
            print(f"Nome da aba: {sheet['properties']['title']}")
            print(f"ID da aba: {sheet['properties']['sheetId']}")

        # Tenta ler um range muito simples
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range="A1:B1"
        ).execute()

        print("\nConteúdo de A1:B1:")
        print(result.get('values', []))

    except Exception as e:
        print(f"Erro no teste: {e}")


if __name__ == "__main__":

    modo = input("Escolha o modo (1 para busca única, 2 para processar planilha, 3 modo de teste): ")

    if modo == "1":
        # Seu código original de busca única
        while True:
            date_outbound = str(input("Qual a data do voo de ida responda em YYYY-MM-DD: "))
            if verify_format(date_outbound):
                break

        while True:
            date_return = str(input("Qual a data do voo de volta responda em YYYY-MM-DD: "))
            if verify_format(date_return):
                break

        cidade_departure = str(input("De qual cidade esta saindo: "))
        cidade_arrival = str(input("Em qual cidade vai chegar: "))

        search_flights(cidade_departure, cidade_arrival,
                       date_outbound, date_return)

    elif modo == "2":
        # Processa dados da planilha
        process_sheet_data(SPREADSHEET_ID)
    elif modo == "3":
        test_sheet_access(SPREADSHEET_ID)

    else:
        print("Modo inválido!")
