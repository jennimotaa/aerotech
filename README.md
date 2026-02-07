
---

# ✈️ SkyCargo - Torre de Controle Logística (Case Sênior)

A **SkyCargo** é especializada no transporte de cargas de altíssima criticidade, como órgãos para transplante e peças de maquinário pesado. Este projeto substitui o monitoramento manual da Infraero por uma **Torre de Controle Automatizada**, garantindo que a logística de solo esteja pronta no segundo exato do pouso.

---

## 📌 Sobre o Projeto

Desenvolvido como desafio final do bootcamp na **Generation Brasil**, em parceria com **CashMe** e **Cyrela**, o sistema cruza telemetria em tempo real com dados climáticos para eliminar a incerteza operacional.

### 🛠️ Tecnologias Utilizadas

* 
**Linguagem:** Python (Coleta via APIs e Tratamento de Dados).


* 
**Banco de Dados:** MySQL (Modelagem Relacional e Índices de Performance).


* 
**Visualização:** Power BI (DAX avançado, Design UI/UX e Storytelling).


* 
**APIs:** OpenSky (Telemetria ADSB) e Open-Meteo (Condições Climáticas).



---

## 🚀 Funcionalidades Principais

* 
**Cálculo Geodésico:** Rastreio físico preciso da aeronave utilizando Latitude e Longitude.


* 
**ETA Ajustado:** Algoritmo inteligente que adiciona **+10min** para ventos fortes e **+15min** para pistas molhadas .


* 
**Matriz de Risco Operacional:** Classificação automática em **Baixo**, **Médio** ou **Crítico** baseada em teto de nuvens e velocidade do vento.


* 
**Alerta de Emergência:** Identificação de descidas bruscas ou desvios de rota fora do padrão de pouso.



---

## 📊 Visualização do Dashboard

> O dashboard foi projetado em **Dark Mode** para reduzir a fadiga visual dos operadores da Torre de Controle.

* 
**Página 1:** Visão Geral da Frota e Status de Pontualidade.


* 
**Página 2:** Telemetria Individualizada (Voo PSJTP) e Gráficos de Descida.


* 
**Página 3:** Mapas de Calor e Distribuição de Risco por Aeroporto.



---

## 📂 Como Utilizar este Repositório

Para replicar a estrutura da Torre de Controle em seu ambiente local, siga os passos abaixo:

### 1️⃣ Preparação do Banco de Dados

Execute o arquivo `schema.sql` no seu servidor MySQL. Ele criará as tabelas `FACT_VOO_TELEMETRIA` e `FACT_CONDICOES_POUSO` com os índices necessários para alta performance.

### 2️⃣ Configuração de Credenciais

No arquivo `functions.py`, localize o dicionário de configuração e insira suas credenciais locais:

```python
DB_CONFIG = {
    'host': 'seu_host',
    'user': 'seu_usuario',
    'password': 'sua_senha'
}

```

### 3️⃣ Execução do Monitoramento

Para iniciar a coleta de dados e atualização do banco, execute o script principal:

```bash
python update_db.py

```

*Este script utiliza as funções contidas em `functions.py` para rodar o loop de monitoramento a cada 5 minutos.*

---

## 🔮 Próximos Passos

* **Machine Learning:** Implementação de modelos (XGBoost) para prever o ETA com base no histórico de órbitas de espera.
* **Dados Premium:** Integração com provedores de satélite para cobertura em áreas de baixa captação ADSB.

---

## 👥 Agradecimentos e Equipe

* **Desenvolvedores:** João Victor Ravazzi Ferretti, Andrey Alves Miranda, **Carrie Jenniffer Alves Mota**, Juliana Malheiros, Leandro Falasca.
* **Mentoria:** Luiz Chiavini e Samuel Reginatto.
* **Apoio:** Generation Brasil, Grupo Cyrela e CashMe.

---

**Pronta para novos desafios em Engenharia de Dados e BI!** 🚀
