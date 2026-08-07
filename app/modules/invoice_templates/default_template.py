DEFAULT_INVOICE_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Factura #{{ invoice_number }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    color: #1a1a1a;
    line-height: 1.4;
  }
  @media screen {
    body { max-width: 800px; margin: 40px auto; padding: 30px; background: #f5f5f5; }
    .invoice-page { background: #fff; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .no-print { display: block; margin-bottom: 16px; }
    .no-print button {
      padding: 8px 20px; font-size: 14px; cursor: pointer;
      background: #2563eb; color: #fff; border: none; border-radius: 4px;
    }
  }
  @media print {
    body { margin: 0; padding: 20px; }
    .no-print { display: none; }
    .invoice-page { padding: 0; }
  }
  .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 2px solid #2563eb; padding-bottom: 16px; }
  .header-left h1 { font-size: 22px; color: #2563eb; margin-bottom: 4px; }
  .header-left p { font-size: 12px; color: #666; }
  .header-right { text-align: right; }
  .header-right h2 { font-size: 18px; color: #333; text-transform: uppercase; letter-spacing: 2px; }
  .header-right p { font-size: 12px; color: #666; }
  .info { display: flex; justify-content: space-between; margin-bottom: 24px; }
  .info-box { width: 48%; }
  .info-box h3 { font-size: 11px; text-transform: uppercase; color: #888; margin-bottom: 6px; letter-spacing: 1px; }
  .info-box p { font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
  thead th { background: #f8f9fa; text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase; color: #666; border-bottom: 2px solid #dee2e6; }
  tbody td { padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 12px; }
  tbody td.num { text-align: right; }
  tbody td.qty { text-align: center; }
  .totals { width: 40%; margin-left: auto; }
  .totals table { width: 100%; }
  .totals td { padding: 4px 10px; font-size: 12px; }
  .totals td:last-child { text-align: right; }
  .totals .grand td { font-weight: bold; font-size: 15px; border-top: 2px solid #2563eb; padding-top: 8px; }
  .payments { margin-top: 20px; border-top: 1px solid #dee2e6; padding-top: 12px; }
  .payments h3 { font-size: 11px; text-transform: uppercase; color: #888; margin-bottom: 8px; letter-spacing: 1px; }
  .payments table { width: 60%; }
  .footer { margin-top: 30px; border-top: 1px solid #dee2e6; padding-top: 10px; text-align: center; font-size: 10px; color: #999; }
  {% if tenant_logo_url %}
  .logo { max-width: 150px; max-height: 60px; margin-bottom: 8px; }
  {% endif %}
</style>
</head>
<body>

<div class="no-print">
  <button onclick="window.print()">Imprimir</button>
</div>

<div class="invoice-page">

  <div class="header">
    <div class="header-left">
      {% if tenant_logo_url %}<img class="logo" src="{{ tenant_logo_url }}" alt="Logo">{% endif %}
      <h1>{{ tenant_name }}</h1>
      {% if tenant_business_id %}<p>{{ tenant_business_id }}</p>{% endif %}
    </div>
    <div class="header-right">
      <h2>Factura</h2>
      <p>Nº {{ invoice_number }}</p>
      <p>{{ invoice_date_short }}</p>
    </div>
  </div>

  <div class="info">
    <div class="info-box">
      <h3>Cliente</h3>
      <p>{{ customer_name }}</p>
      {% if customer_document %}<p>Doc: {{ customer_document }}</p>{% endif %}
      {% if customer_email %}<p>{{ customer_email }}</p>{% endif %}
      {% if customer_phone %}<p>{{ customer_phone }}</p>{% endif %}
      {% if customer_address %}<p>{{ customer_address }}</p>{% endif %}
    </div>
    <div class="info-box">
      <h3>Detalle</h3>
      <p>Fecha: {{ invoice_date }}</p>
      <p>Estado: {{ status }}</p>
      <p>Pago: {{ payment_status }}</p>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Producto</th>
        <th class="qty">Cant.</th>
        <th class="num">P. Unitario</th>
        <th class="num">Subtotal</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      <tr>
        <td>{{ item.product_name }}</td>
        <td class="qty">{{ item.quantity }}</td>
        <td class="num">{{ item.unit_price }}</td>
        <td class="num">{{ item.subtotal }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td>Subtotal</td><td>{{ subtotal }}</td></tr>
      <tr><td>Impuestos</td><td>{{ tax_total }}</td></tr>
      <tr class="grand"><td>Total</td><td>{{ total }}</td></tr>
    </table>
  </div>

  {% if payments %}
  <div class="payments">
    <h3>Pagos</h3>
    <table>
      <thead>
        <tr>
          <th>Método</th>
          <th class="num">Monto</th>
          <th>Referencia</th>
        </tr>
      </thead>
      <tbody>
        {% for payment in payments %}
        <tr>
          <td>{{ payment.method }}</td>
          <td class="num">{{ payment.amount }}</td>
          <td>{{ payment.reference or '-' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if notes %}
  <div class="payments">
    <h3>Notas</h3>
    <p>{{ notes }}</p>
  </div>
  {% endif %}

  <div class="footer">
    <p>{{ tenant_name }} — Generado el {{ invoice_date }}</p>
  </div>

</div>

<script>
  {% if auto_print %}
  window.onload = function() { window.print(); };
  {% endif %}
</script>
</body>
</html>"""
