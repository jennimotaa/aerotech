import requests
import time
import math
import os
import logging
from geopy.distance import geodesic
import mysql.connector
from datetime import datetime

# =========================================================
#  SKYCARGO LOGISTICS INTELLIGENCE - AERO OPS PREDICTOR
#  main.py (mantém base/prints do original + correções)
#
#  Inclui:
#   ✅ ETA Real sem somar atraso climático
#   ✅ Open-Meteo prob correta (alinha current.time com hourly.time)
#   ✅ Risco: vento + chuva_mm + probabilidade
#   ✅ Destino: score alinhamento + distância
#   ✅ Commit do clima mesmo quando não tem voo
#   ✅ Senha via ENV VAR (DB_PASSWORD) com fallback
#   ✅ Emergência com menos falso positivo (baro_rate / speed drop + contexto)
# =========================================================

# --- CONFIGURAÇÕES & CONSTANTES ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),  # definir via variável de ambiente
    "database": os.getenv("DB_NAME", "aero_ops"),
    "use_pure": True,
}

# Aeroportos monitorados
AEROPORTOS = {
    "SBGR": {"nome": "Guarulhos", "coords": (-23.4356, -46.4731), "alt_ref": 2430},
    "SBSP": {"nome": "Congonhas", "coords": (-23.6261, -46.6564), "alt_ref": 2631},
    "SBKP": {"nome": "Viracopos", "coords": (-23.0074, -47.1344), "alt_ref": 2170},
}

RAIO_ANALISE_KM = 150     # Busca focada em SP
RAIO_CRITICO_KM = 80      # Raio para validar "chegada"

# Risco (ajuste se quiser)
WIND_CRIT_KMH = 30
PROB_CHUVA_CRIT = 70
PROB_CHUVA_MED = 30
CHUVA_MM_CRIT = 0.5
CHUVA_MM_MED = 0.1

# Confirmação de destino
MIN_SCORE_CONFIRMAR = 85
PESO_ALINHAMENTO = 0.70
PESO_DISTANCIA = 0.30

# Emergência (menos falso positivo)
BARO_RATE_SUBIDA_CORTA = 1200     # ft/min (muito alto, costuma ser decolagem/arremetida)
BARO_RATE_QUEDA_ALERTA = -2500    # ft/min (queda bem agressiva)
SPEED_DROP_ALERTA = 180           # km/h (queda brusca entre ciclos)
ALT_MIN_ALERTA = 5000             # ft
DIST_MIN_ALERTA = 50              # km

# Tempo de ciclo
SLEEP_SECONDS = 300

# Configuração de Cores para Terminal
class Cores:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

# Logging Básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# =========================================================
#  CLASSE: GERENCIADOR DE BANCO DE DADOS
# =========================================================
class AeroDatabase:
    """Gerencia conexões e persistência de dados de forma eficiente (Batch)"""

    def __init__(self):
        self.conn = None
        self.cursor = None

    def conectar(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            logging.info("Conectado ao Banco de Dados.")
        except Exception as e:
            logging.error(f"Falha ao conectar no BD: {e}")

    def desconectar(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    @staticmethod
    def calcular_risco(clima: dict) -> str:
        """Risco usando vento + chuva_mm + probabilidade"""
        vento = float(clima.get("vento", 0) or 0)
        chuva = float(clima.get("chuva", 0) or 0)
        prob = float(clima.get("prob", 0) or 0)

        if vento >= WIND_CRIT_KMH or chuva >= CHUVA_MM_CRIT or prob >= PROB_CHUVA_CRIT:
            return "Critico"
        if chuva >= CHUVA_MM_MED or prob >= PROB_CHUVA_MED:
            return "Medio"
        return "Baixo"

    def salvar_ciclo(self, dados_clima_map, voos_identificados_map):
        """
        Salva TODO o ciclo de uma vez.
        1. Insere dados de clima (Um por aeroporto).
        2. Insere dados de voos vinculados ao ID do clima.
        """
        if not self.conn or not self.conn.is_connected():
            self.conectar()

        try:
            # 1) Salvar Clima e obter IDs
            clima_ids = {}
            sql_clima = (
                "INSERT INTO FACT_CONDICOES_POUSO "
                "(aeroporto_destino, vento_velocidade, chuva_mm, risco_calculado) "
                "VALUES (%s, %s, %s, %s)"
            )

            for icao, clima in dados_clima_map.items():
                risco = self.calcular_risco(clima)
                self.cursor.execute(sql_clima, (icao, clima["vento"], clima["chuva"], risco))
                clima_ids[icao] = self.cursor.lastrowid

            # ✅ Commit do clima mesmo quando não tiver voo
            if not voos_identificados_map:
                self.conn.commit()
                logging.info("Ciclo persistido: clima salvo (0 voos).")
                return

            # 2) Salvar Voos (Batch)
            sql_voo = (
                "INSERT INTO FACT_VOO_TELEMETRIA "
                "(callsign, aeroporto_alvo, latitude, longitude, altitude_pes, "
                " velocidade_kmh, distancia_destino_km, status_pontualidade, "
                " tendencia_velocidade, motivo_atraso, alerta_emergencia, eta_real_min, id_clima_fk) "
                "VALUES (%s, %s, %s, %s, %s, "
                "        %s, %s, %s, "
                "        %s, %s, %s, %s, %s)"
            )

            valores_voos = []
            for aviao in voos_identificados_map.values():
                icao_alvo = aviao["aeroporto_alvo"]
                id_clima = clima_ids.get(icao_alvo)

                valores_voos.append(
                    (
                        aviao["callsign"],
                        icao_alvo,
                        aviao["lat"],
                        aviao["lon"],
                        aviao["alt"],
                        aviao["vel"],
                        aviao["dist"],
                        aviao["status"],
                        aviao["tendencia"],
                        aviao["motivo"],
                        aviao["emergencia"],
                        aviao["eta_real"],  # ✅ ETA REAL (sem atraso)
                        id_clima,
                    )
                )

            if valores_voos:
                self.cursor.executemany(sql_voo, valores_voos)

            self.conn.commit()
            logging.info(f"Ciclo persistido: {len(valores_voos)} voos salvos.")

        except Exception as e:
            logging.error(f"Erro ao salvar ciclo no banco: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass


# =========================================================
#  CLASSE: INTELIGÊNCIA GEODÉSICA
# =========================================================
class AeroAnalytics:
    @staticmethod
    def calcular_bearing(lat1, lon1, lat2, lon2):
        """Calcula o ângulo de direção (Azimute) entre dois pontos"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    @staticmethod
    def calcular_score_afinidade(aviao_lat, aviao_lon, aviao_track, aero_coords):
        """
        SCORE (0-100) da probabilidade do avião estar indo para o aeroporto.
        Agora combina: alinhamento (track vs bearing) + distância (penaliza longe).
        """
        distancia = geodesic((aviao_lat, aviao_lon), aero_coords).kilometers
        if distancia > RAIO_ANALISE_KM:
            return 0, distancia

        bearing_ideal = AeroAnalytics.calcular_bearing(aviao_lat, aviao_lon, aero_coords[0], aero_coords[1])

        diff_angulo = abs(aviao_track - bearing_ideal)
        diff_angulo = min(diff_angulo, 360 - diff_angulo)

        # Alinhamento: 100 se perfeito, 0 se 50°+ fora
        score_alinhamento = max(0, 100 - (diff_angulo * 2))

        # Distância: 100 perto, 0 no limite do raio
        score_dist = max(0, 100 * (1 - (distancia / RAIO_ANALISE_KM)))

        score_total = (PESO_ALINHAMENTO * score_alinhamento) + (PESO_DISTANCIA * score_dist)
        return score_total, distancia


# =========================================================
#  CLASSE: CONTROLADOR DE VOOS (CORE)
# =========================================================
class FlightSeer:
    def __init__(self):
        self.db = AeroDatabase()
        self.historico = {}  # callsign -> cache para tendência/emergência/histerese

    def buscar_clima(self, coords):
        """
        Busca Clima (Resiliente e Preciso)
        ✅ pega precipitation_probability correta alinhando current.time com hourly.time
        """
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={coords[0]}&longitude={coords[1]}"
            "&current=precipitation,wind_speed_10m"
            "&hourly=precipitation_probability"
            "&forecast_days=1"
            "&timezone=auto"
        )

        try:
            r = requests.get(url, timeout=6).json()
            current = r.get("current", {}) or {}
            hourly = r.get("hourly", {}) or {}

            current_time = current.get("time")  # ex: '2026-01-30T12:00'
            times = hourly.get("time", []) or []
            probs = hourly.get("precipitation_probability", []) or []

            prob_atual = 0
            if current_time and times and probs:
                try:
                    idx = times.index(current_time)
                    prob_atual = probs[idx] if idx < len(probs) else 0
                except ValueError:
                    # fallback: usa hora local (melhor do que quebrar)
                    hora_atual = datetime.now().hour
                    prob_atual = probs[hora_atual] if len(probs) > hora_atual else probs[0]

            return {
                "chuva": float(current.get("precipitation", 0) or 0),
                "vento": float(current.get("wind_speed_10m", 0) or 0),
                "prob": float(prob_atual or 0),
            }
        except Exception as e:
            logging.error(f"Erro ao buscar clima: {e}")
            return {"chuva": 0.0, "vento": 0.0, "prob": 0.0}

    def _calc_atraso_clima_min(self, clima_dest: dict) -> int:
        """Atraso por clima (para status/motivo, mas NÃO soma no ETA real)"""
        vento = float(clima_dest.get("vento", 0) or 0)
        chuva = float(clima_dest.get("chuva", 0) or 0)
        prob = float(clima_dest.get("prob", 0) or 0)

        if vento >= WIND_CRIT_KMH or chuva >= CHUVA_MM_CRIT or prob >= PROB_CHUVA_CRIT:
            return 15
        return 0

    def _tendencia_velocidade(self, callsign: str, gs: float) -> str:
        if callsign not in self.historico:
            return "Estavel"
        prev_gs = float(self.historico[callsign].get("gs", gs))
        diff = gs - prev_gs
        if diff > 50:
            return "Aumentando"
        if diff < -50:
            return "Reduzindo"
        return "Estavel"

    def _alerta_emergencia(self, callsign: str, alt: float, dist_km: float, baro_rate: float, gs: float) -> int:
        """
        ✅ Menos falso positivo:
        - contexto: alt baixa mas ainda longe (não é final de aproximação)
        - + queda agressiva (baro_rate muito negativo) OU queda brusca de velocidade entre ciclos
        """
        prev = self.historico.get(callsign, {})
        prev_gs = float(prev.get("gs", gs))

        queda_agressiva = float(baro_rate or 0) <= BARO_RATE_QUEDA_ALERTA
        speed_drop = (prev_gs - gs) >= SPEED_DROP_ALERTA
        contexto = (alt <= ALT_MIN_ALERTA and dist_km >= DIST_MIN_ALERTA)

        if contexto and (queda_agressiva or speed_drop):
            return 1
        return 0

    def executar_ciclo(self):
        os.system("cls" if os.name == "nt" else "clear")
        print(f"{Cores.HEADER}{Cores.BOLD}==================================================================")
        print("✈️  SKYCARGO LOGISTICS INTELLIGENCE - AERO OPS PREDICTOR V3.1 (Refined)")
        print(f"=================================================================={Cores.ENDC}")

        # 1) Clima (Cache)
        clima_map = {}
        for icao, dados in AEROPORTOS.items():
            clima_map[icao] = self.buscar_clima(dados["coords"])

        # 2) Buscar Aviões (Global)
        centro_lat, centro_lon = -23.5, -46.6  # SP Centro
        url_radar = f"https://api.adsb.lol/v2/lat/{centro_lat}/lon/{centro_lon}/dist/180"

        voos_identificados_map = {}  # callsign -> dados

        try:
            resp = requests.get(url_radar, timeout=12).json()
            lista_avioes = resp.get("ac", [])

            # 3) Lógica Melhorada de Destino
            for a in lista_avioes:
                callsign = (a.get("flight", "") or "").strip()
                if not callsign or len(callsign) < 3:
                    continue

                lat, lon = a.get("lat"), a.get("lon")
                if lat is None or lon is None:
                    continue

                track = float(a.get("track", 0) or 0)

                alt = a.get("alt_baro", "ground")
                if alt == "ground":
                    alt = 0.0
                else:
                    alt = float(alt or 0)

                baro_rate = float(a.get("baro_rate", 0) or 0)

                gs = float(a.get("gs", 0) or 0) * 1.852  # knots -> km/h
                if gs < 50:
                    continue

                # --- FILTROS DE INTELIGÊNCIA ---
                # 1. Filtro de subida MUITO agressiva (decolagem/arremetida)
                if baro_rate > BARO_RATE_SUBIDA_CORTA:
                    continue

                melhor_score = -9999
                melhor_dest = None
                dist_para_melhor = None

                for icao, aero_data in AEROPORTOS.items():
                    score, dist = AeroAnalytics.calcular_score_afinidade(lat, lon, track, aero_data["coords"])

                    # 2. Filtro vertical (evitar alto demais perto do aeroporto)
                    # Se está muito perto e muito alto, tende a ser sobrevoo
                    if dist < 80 and alt > 10000:
                        score -= 40

                    # Histerese: se antes estava indo pra um target e agora se afasta muito, penaliza
                    if callsign in self.historico:
                        prev = self.historico[callsign]
                        if prev.get("target") == icao:
                            prev_dist = float(prev.get("dist", dist))
                            if dist > prev_dist + 5:
                                score -= 30

                    # Perfil vertical (glideslope) refinado
                    altura_relativa = alt - aero_data["alt_ref"]
                    max_altura_viavel = (dist * 450) + 1500  # ft/km + buffer
                    if altura_relativa > max_altura_viavel:
                        score -= 50

                    if dist < 10 and altura_relativa > 3000:
                        score -= 100

                    if score > melhor_score:
                        melhor_score = score
                        melhor_dest = icao
                        dist_para_melhor = dist

                # Só confirma se tiver certeza (Score >= MIN_SCORE_CONFIRMAR)
                if melhor_dest and dist_para_melhor is not None and melhor_score >= MIN_SCORE_CONFIRMAR:
                    clima_dest = clima_map[melhor_dest]

                    # Risco e atraso por clima (não soma no ETA real)
                    atraso_min = self._calc_atraso_clima_min(clima_dest)

                    status = "No Horario"
                    motivo = "Operacao Normal"
                    if atraso_min > 0:
                        status = "Atrasado"
                        motivo = "Condicoes Meteorologicas"

                    # ✅ ETA REAL (sem atraso)
                    eta_real = ((dist_para_melhor / gs) * 60) if gs > 0 else 0.0

                    # Tendência e emergência
                    tendencia = self._tendencia_velocidade(callsign, gs)
                    emergencia = self._alerta_emergencia(callsign, alt, dist_para_melhor, baro_rate, gs)
                    if emergencia:
                        status = "EMERGÊNCIA"
                        motivo = "Desvio / Perfil Anomalo"

                    voos_identificados_map[callsign] = {
                        "callsign": callsign,
                        "aeroporto_alvo": melhor_dest,
                        "lat": lat,
                        "lon": lon,
                        "alt": alt,
                        "vel": gs,
                        "dist": dist_para_melhor,
                        "status": status,
                        "tendencia": tendencia,
                        "motivo": motivo,
                        "eta_real": eta_real,
                        "emergencia": emergencia,
                    }

                    # Atualiza histórico (para tendência / histerese / emergência)
                    self.historico[callsign] = {
                        "gs": gs,
                        "alt": alt,
                        "time": time.time(),
                        "target": melhor_dest,
                        "dist": dist_para_melhor,
                        "baro_rate": baro_rate,
                    }

            # 4) EXIBIÇÃO VISUAL (mantém estilo original)
            voos_por_aero = {icao: [] for icao in AEROPORTOS}
            for v in voos_identificados_map.values():
                if v["aeroporto_alvo"] in voos_por_aero:
                    voos_por_aero[v["aeroporto_alvo"]].append(v)

            for icao, info in AEROPORTOS.items():
                clima = clima_map[icao]
                pista_status = f"{Cores.GREEN}SECA{Cores.ENDC}" if clima["chuva"] < 0.2 else f"{Cores.FAIL}MOLHADA{Cores.ENDC}"
                risco_txt = self.db.calcular_risco(clima)

                print(f"\n{Cores.BOLD}📍 AEROPORTO: {info['nome']} ({icao}){Cores.ENDC}")
                print(f"   [Pista: {pista_status} | Vento: {clima['vento']}km/h | Prob. Chuva: {clima['prob']}% | Risco: {risco_txt}]")
                print(f"   {'-'*60}")

                lista_voos = voos_por_aero[icao]
                if not lista_voos:
                    print(f"   {Cores.BLUE}Nenhum voo em aproximação detectado.{Cores.ENDC}")
                else:
                    # Ordenar por distância (igual seu original)
                    lista_voos.sort(key=lambda x: x["dist"])
                    for v in lista_voos:
                        color_status = Cores.WARNING if v["status"] == "EMERGÊNCIA" else (Cores.GREEN if v["status"] == "No Horario" else Cores.FAIL)
                        print(
                            f"   ✈️  {Cores.BOLD}{v['callsign']:8}{Cores.ENDC} | "
                            f"Alt: {int(v['alt']):5}ft | Dist: {int(v['dist']):3}km | "
                            f"ETA: {int(v['eta_real']):3}min | "
                            f"Status: {color_status}{v['status']:10}{Cores.ENDC}"
                        )

            # 5) Persistir no BD
            self.db.salvar_ciclo(clima_map, voos_identificados_map)

        except Exception as e:
            print(f"Erro no ciclo de radar: {e}")

    def loop(self):
        try:
            while True:
                self.executar_ciclo()
                print("\nEsperando 5 minutos para o próximo ciclo...")
                time.sleep(SLEEP_SECONDS)
        except KeyboardInterrupt:
            print("Encerrando...")
            self.db.desconectar()


if __name__ == "__main__":
    app = FlightSeer()
    app.loop()
