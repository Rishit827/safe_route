from app.collectors.sachet import parse_sachet


def test_parse_direct_cap_circle():
    xml = '''<?xml version="1.0"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>abc-123</identifier><sender>NDMA</sender><expires>2026-10-23T00:00:00+00:00</expires>
      <info><event>Flood warning</event><headline>Flood near river</headline>
      <description>Heavy rainfall and possible flooding</description><severity>Severe</severity>
      <area><areaDesc>Test district</areaDesc><circle>31.6340,74.8723 2.5</circle></area></info>
    </alert>'''
    alerts = parse_sachet(xml)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["source"] == "sachet"
    assert alert["type"] == "flood"
    assert alert["lat"] == 31.634
    assert alert["lng"] == 74.8723
    assert alert["radius_m"] == 2500
    assert alert["severity"] == 4
    assert alert["admin_status"] == "pending"


def test_parse_rss_item_with_embedded_cap():
    xml = '''<rss><channel><item><title>Flood warning</title><description><![CDATA[
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>rss-1</identifier>
    <info><event>Flood</event><headline>Flood alert</headline><severity>Extreme</severity>
    <area><areaDesc>Punjab</areaDesc><circle>31.5,75.0 1</circle></area></info></alert>
    ]]></description></item></channel></rss>'''
    alerts = parse_sachet(xml)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == 5
    assert alerts[0]["lat"] == 31.5


def test_invalid_sachet_payload_returns_empty_list():
    assert parse_sachet("not xml or json") == []
