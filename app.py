import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from dotenv import load_dotenv
from selenium_stealth import stealth
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


load_dotenv()


# --- Configurações ---
URL_DO_INGRESSO = os.getenv("URL_DO_INGRESSO", "https://buyticketbrasil.com/evento/guns-n%C2%B4roseswldw?data=Oct%2025%2C%202025%2010%3A00%20pm&evento_local=1749578162772x188881550261878800")
PRECO_LIMITE = float(os.getenv("PRECO_LIMITE", "600.00"))
PADRAO_REGEX = r"Meia Estudante\s*R\$\s*([\d.,]+)\s*Comprar"
INTERVALO_VERIFICACAO = int(os.getenv("INTERVALO_VERIFICACAO", "120")) 
INTERVALO_STATUS = int(os.getenv("INTERVALO_STATUS", "900"))
HEADLESS = os.getenv("HEADLESS", "1").lower() == "1"

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_notificacao_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token ou chat_id ausente.")
        return
    
    url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    
    try:
        r = requests.post(url_api, data=payload, timeout=10)
        print("Notificação enviada" if r.ok else f"Erro: {r.text}")
    except Exception as e:
        print(f"Falha Telegram: {e}")
        
def verificar_preco(driver):
    # Tenta a operação completa até 3 vezes para lidar com elementos 'stale'
    for attempt in range(3):
        try:
            driver.get(URL_DO_INGRESSO)
            wait = WebDriverWait(driver, 20) # Um pouco mais de tempo não faz mal

            # Tipo de ingresso
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Tipo de ingresso')]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Cadeira Inferior']"))).click()

            # Categoria
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Categoria')]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[text()='Meia Estudante']"))).click()
            
            # Pequena pausa para a UI reagir após o último clique
            time.sleep(2)

            # --- Bloco Crítico ---
            # Localiza o elemento e extrai o texto na mesma tentativa
            elemento_preco = wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(., 'Meia Estudante') and contains(., 'R$')]")))
            texto_do_elemento = elemento_preco.text
            
            match = re.search(PADRAO_REGEX, texto_do_elemento)
            if not match:
                print("Regex não encontrou o padrão de preço no texto do elemento.")
                return None # Se o regex falhar, não adianta tentar de novo
            
            valor = float(match.group(1).replace(".", "").replace(",", "."))
            return valor # Sucesso! Retorna o valor e sai da função.

        except StaleElementReferenceException:
            print(f"Elemento 'stale' detectado. Tentativa {attempt + 1} de 3.")
            time.sleep(2) # Espera 2 segundos antes de tentar novamente
            continue # Continua para a próxima iteração do loop

        except (TimeoutException, NoSuchElementException):
            print("Elemento não encontrado ou tempo de espera excedido. Verificando screenshot...")
            driver.save_screenshot("/tmp/debug.png")

            return None # Se o elemento nunca aparecer, desistimos
            
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
    
    # Se o loop terminar sem sucesso
    print("Falhou em obter o preço após 3 tentativas.")
    return None


if __name__ == "__main__":
    last_status_update = 0
    driver = None

    try:
        # Inicia o driver uma única vez
        options = webdriver.ChromeOptions()

        if HEADLESS:
            options.add_argument("--headless=new")

        # Configs padrão para rodar em container
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36')
        options.add_argument("--user-data-dir=/tmp/user-data")

        # Desabilita flags que entregam a automação
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
        
        print("Iniciando monitoramento de preços...")
        print(f"URL: {URL_DO_INGRESSO}"
              f"\nLimite: R$ {PRECO_LIMITE:.2f}"
              f"\nIntervalo de verificação: {INTERVALO_VERIFICACAO//60} min"
              f"\nIntervalo de status: {INTERVALO_STATUS//60} min"
              f"\nModo headless: {'Sim' if HEADLESS else 'Não'}"
              f"\nTELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}"
                f"\nTELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}..." if TELEGRAM_BOT_TOKEN else "None"
              )

        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Verificando...")
            preco = verificar_preco(driver)

            if preco:
                print(f"Preço atual: R$ {preco:.2f}")
                if preco < PRECO_LIMITE:
                    enviar_notificacao_telegram(
                        f"🚨 <b>ALERTA!</b>\nMeia Estudante por <b>R$ {preco:.2f}</b>\n{URL_DO_INGRESSO}"
                    )

                agora = time.time()
                if agora - last_status_update >= INTERVALO_STATUS:
                    enviar_notificacao_telegram(
                        f"Status: Meia Estudante R$ {preco:.2f} (limite R$ {PRECO_LIMITE:.2f})"
                    )
                    last_status_update = agora
            else:
                print("Preço não encontrado.")

            print(f"Aguardando {INTERVALO_VERIFICACAO//60} min...")
            time.sleep(INTERVALO_VERIFICACAO)

    except KeyboardInterrupt:
        print("Interrompido pelo usuário.")
    finally:
        if driver:
            driver.quit()
            print("Navegador fechado.")
