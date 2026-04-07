from backend.analytics_engine.water_chemistry_analytics.ph_service import get_ph_analysis

result = get_ph_analysis("tank_1_test", "24h")
print(result)