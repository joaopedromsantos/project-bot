# --- Estágio 1: Base e Dependências ---
# Usamos a imagem oficial do Python baseada no Alpine Linux, que é super leve.
FROM python:3.11-alpine

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Instala as dependências do sistema operacional necessárias para o Selenium rodar com o Chrome (Chromium).
# 'chromium' é o navegador e 'chromium-chromedriver' é o driver.
# '--no-cache' garante que o cache do gerenciador de pacotes não seja armazenado, mantendo a imagem pequena.
RUN apk add --no-cache chromium chromium-chromedriver nss freetype harfbuzz ttf-freefont


# Copia o arquivo de dependências Python para o contêiner.
# Fazer isso antes de copiar o resto do código aproveita o cache do Docker.
# Se o requirements.txt não mudar, o Docker não reinstalará tudo a cada build.
COPY requirements.txt .

# Instala as bibliotecas Python.
# '--no-cache-dir' desabilita o cache do pip para economizar espaço.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto dos arquivos da sua aplicação (o script app.py e o .env).
COPY . .

# --- Estágio 2: Comando de Execução ---
# Define o comando que será executado quando o contêiner iniciar.
ENV PORT=8080

CMD ["python", "app.py"]