import jenkins
import gspread
from google.oauth2 import service_account
from tokens import jenkins_link
class JenkinsGoogleSheetsIntegration:
    def __init__(self, jenkins_url, spreadsheet_id):
        self.server = jenkins.Jenkins(jenkins_url)
        self.spreadsheet_id = spreadsheet_id

    def fetch_build_timestamp(self, job_name, build_job):
        build_info = self.server.get_build_info(job_name, build_job)
        return build_info['timestamp']
    def fetch_lastbuildnumber(self, job_name):
        lastbuild_number = self.server.get_job_info(job_name)['lastCompletedBuild']['number']
        return lastbuild_number
    def fetch_build_info_message(self, job_name, build_job):
        try:
            build_info = self.server.get_build_info(job_name, build_job)
            if 'changeSets' in build_info and build_info['changeSets']:
                return build_info['changeSets'][0]['items'][0]['msg']
            else:
                return "Mensagem não retornada, verificar manualmente na página do build"
        except Exception as e:
            return print(f"Ocorreu um erro ao buscar a mensagem do build: {e}")

    def fetch_build_info_date(self, job_name, build_job):
        try:
            build_info = self.server.get_build_info(job_name, build_job)
            if 'changeSets' in build_info and build_info['changeSets']:
                return build_info['changeSets'][0]['items'][0]['date']
            else:
                return "Data não retornada, verificar manualmente na página do build"
        except Exception as e:
            return print(f"Ocorreu um erro ao buscar a data do build: {e}")

    @staticmethod
    def fetch_google_sheets_data(spreadsheet, worksheet_name, lastbuild_sheet, build_job, msg,
                                 data):
        # #conexão com a planilha
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets",
                      "https://www.googleapis.com/auth/drive"]
            credentials = service_account.Credentials.from_service_account_file("credenciais.json", scopes=scopes)
            client = gspread.authorize(credentials)
            sheet = client.open(spreadsheet).worksheet(worksheet_name)

            next_line = 1
            while sheet.cell(next_line, 1).value:
                next_line += 1

            lastbuild_sheet = int(lastbuild_sheet)
            # Verificar se o valor do build na planilha é menor que o valor do build conferido
            if lastbuild_sheet < build_job:
                # Inserir uma nova linha entre a primeira e a segunda linha
                values_to_insert = [[build_job, data, msg]]
                sheet.insert_row(values_to_insert[0], index=next_line)

            elif lastbuild_sheet > build_job:
                print("O valor do build na planilha é maior que o Jenkins.")

            else:
                print("Este build já está na planilha.")

        except Exception as e:
            print(f"Erro ao atualizar a planilha: {e}")
def main():
    jenkins_url = jenkins_link
    spreadsheet = "V2.2310 - Release Note"
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]

    credentials = service_account.Credentials.from_service_account_file("credenciais.json", scopes=scopes)
    client = gspread.authorize(credentials)

    systems = {
        '1': {'job_name': 'Contabil/v2.2310', 'worksheet_name': 'Contábil'},
        '2': {'job_name': 'Scritta/v2.2310', 'worksheet_name': 'Scritta'},
        '3': {'job_name': 'Persona/v2.2310', 'worksheet_name': 'Persona'},
        '4': {'job_name': 'Estoque-Compras/v2.2310', 'worksheet_name': 'Estoque-Compras'},
        '5': {'job_name': 'PDV2/v2.2310', 'worksheet_name': 'PDV'},
        '6': {'job_name': 'Locacoes/v2.2310', 'worksheet_name': 'Locações'},
        '7': {'job_name': 'CRM/v2.2310', 'worksheet_name': 'CRM'},
        '8': {'job_name': 'Admin/v2.2310', 'worksheet_name': 'Admin'},
        '9': {'job_name': 'Financas-Servicos/v2.2310', 'worksheet_name': 'Finanças-Servicos'}
    }

    jenkins_google_sheets = JenkinsGoogleSheetsIntegration(jenkins_url, spreadsheet)

    installer = 'Instalador/v2.2310'
    user_build_installer = input('Insira os 2 últimos dígitos do instalador que será homologado (Ex: 2.2310.72.0, inserir apenas o 72): ')
    user_build_installer = int(user_build_installer)

    #Processo de conexão com a planilha
    for system_key, system_data in systems.items():
        print(f"Processando sistema: {system_data['worksheet_name']}")
        job_name = system_data['job_name']
        worksheet_name = system_data['worksheet_name']
        sheet = client.open(spreadsheet).worksheet(worksheet_name)

        #Primeiro passo: conferir se a planilha está vazia
        cell_value = sheet.cell(2, 1).value
        if not cell_value:
            timestamp_installer = jenkins_google_sheets.fetch_build_timestamp(installer, user_build_installer)
            lastbuild_number = jenkins_google_sheets.fetch_lastbuildnumber(job_name)
            timestamp_lastbuild = jenkins_google_sheets.fetch_build_timestamp(job_name, lastbuild_number)

            #Pega a marcação temporal do instalador inserido pelo usuário e diminui pelo último até que insira o valor do build presente no instalador
            while timestamp_lastbuild > timestamp_installer:
                lastbuild_number = lastbuild_number - 1
                timestamp_lastbuild = jenkins_google_sheets.fetch_build_timestamp(job_name, lastbuild_number)
                print(f"Este build não está presente no instalador inserido. Build: 2.2310.{lastbuild_number}.0")
            else:
                # Preenche os dados na "primeira linha" caso a primeira linha da página esteja vazia
                print(f"Este build está presente no instalador inserido. Build: 2.2310.{lastbuild_number}.0")
                msg = jenkins_google_sheets.fetch_build_info_message(job_name, lastbuild_number)
                date_time = jenkins_google_sheets.fetch_build_info_date(job_name, lastbuild_number)
                sheet.update_cell(2, 1, lastbuild_number)
                sheet.update_cell(2, 2, date_time)
                sheet.update_cell(2, 3, msg)
                print("Dados inseridos com sucesso")
        else:
            #Caso a primeira linha não esteja vazia, ele deve comparar a marcação temporal do instalador inserido com o numero da marcação do ultimo build da planilha
            column_values = sheet.col_values(1)
            last_filled_row = len(column_values)
            last_value = sheet.cell(last_filled_row, 1).value
            int_last_value = int(last_value)
            timestamp_lastvalue = jenkins_google_sheets.fetch_build_timestamp(job_name,int_last_value)
            timestamp_installer = jenkins_google_sheets.fetch_build_timestamp(installer, user_build_installer)

            while timestamp_lastvalue <= timestamp_installer:
                try:
                    print(f"Este build está no instalador inserido: Build: 2.2310.{int_last_value}.0")
                    msg = jenkins_google_sheets.fetch_build_info_message(job_name, int_last_value)
                    date_time = jenkins_google_sheets.fetch_build_info_date(job_name, int_last_value)
                    result = jenkins_google_sheets.fetch_google_sheets_data(spreadsheet,worksheet_name,last_value,int_last_value,msg,date_time)

                    int_last_value += 1
                    timestamp_lastvalue = jenkins_google_sheets.fetch_build_timestamp(job_name,
                                                                                           int_last_value)

                except jenkins.JenkinsException as e:
                    # caso não tenha o build a mais ele para e pula para o próximo sistema
                    print("Não existem mais builds construidos. Pulando para o próximo sistema.")
                    break

    print("Sistemas finalizados com sucesso. Verificar a planilha.")

if __name__ == "__main__":
    main()
