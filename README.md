✈️ SkyCargo - Torre de Controle Logística (Case Sênior)

------ 📌 Sobre o Projeto ------ 
Este projeto foi desenvolvido como desafio final do bootcamp na Generation Brasil. A SkyCargo transporta cargas críticas (órgãos e maquinário urgente). O objetivo foi substituir o monitoramento manual por uma Torre de Controle Automatizada que utiliza telemetria em tempo real e dados meteorológicos para prever o ETA (Estimated Time of Arrival) real. 


------ 🛠️ Tecnologias Utilizadas: ------ 


Linguagem: Python (Coleta e Tratamento de Dados). 

Banco de Dados: MySQL (Modelagem Relacional e Índices de Performance). 

Visualização: Power BI (DAX avançado, Design UI/UX e Interatividade).

APIs: OpenSky (Telemetria ADSB) e Open-Meteo (Condições Climáticas). 


------ 🚀 Funcionalidades Principais: ------ 


Cálculo Geodésico: Rastreio físico da aeronave via Latitude/Longitude. 

ETA Ajustado: Algoritmo que adiciona +10min em casos de ventos fortes e +15min para pistas molhadas. 

Matriz de Risco: Classificação automática de voos em Baixo, Médio ou Crítico com base no clima e altitude. 

Alerta de Emergência: Identificação automática de descidas bruscas fora do padrão de pouso. 



------ 📊 Visualização do Dashboard ------
<img width="2574" height="1484" alt="image" src="https://github.com/user-attachments/assets/2fe799c6-a18d-45b9-afc9-3b676be198fd" />



------ 📂 Como Utilizar este Repositório ------

Por questões de segurança e proteção de dados, as credenciais de acesso ao banco de dados foram removidas dos scripts. Para replicar o projeto:

1. Banco de Dados: Execute o arquivo schema.sql em seu servidor MySQL local para criar a estrutura das tabelas FACT_VOO_TELEMETRIA e FACT_CONDICOES_POUSO.
2. Configuração: No arquivo functions.py, insira suas credenciais (Host, User e Password) no dicionário DB_CONFIG.
3. Execução: Execute o script functions.py para iniciar o monitoramento em loop (atualização recomendada a cada 5 minutos).


   
------ 🚀 Próximos Passos ------

Machine Learning: Implementação de modelos de regressão (XGBoost/Random Forest) para prever padrões de órbita e refinar o ETA de forma preditiva.

Dados Premium: Transição para APIs de baixa latência para garantir disponibilidade total em escala industrial.



------ 👥 Agradecimentos ------

Equipe: João Victor Ravazzi Ferretti, Andrey Alves Miranda, Carrie Jenniffer Alves Mota, Juliana Malheiros, Leandro Falasca.

Instrutores: Luiz Chiavini e Samuel Reginatto

Apoiadores: Generation Brasil, Grupo Cyrela e CashMe.

------------------------------------------------------


Este projeto demonstra competências em Engenharia de Dados, Business Intelligence e Storytelling com Dados.
