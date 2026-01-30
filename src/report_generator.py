# src/report_generator.py

import os
from datetime import datetime

def generate_bulk_html_report(results: list, output_path: str = "bulk_report.html"):
    """
    Creates a single HTML report summarizing multiple invoices.
    """
    
    # Calculate summary stats
    total_invoices = len(results)
    total_value = sum(float(r.get('total_amount') or 0) for r in results)
    passed_count = sum(1 for r in results if r.get('validation_status') == 'passed')
    
    rows_html = ""
    for idx, res in enumerate(results, 1):
        # Create a mini-table for the items in this invoice
        items_list = ""
        for item in res.get("items", []):
            total_val = item.get('total', 0)
            try:
                total_val = float(total_val)
                items_list += f"<li>{item.get('description', 'Item')} <span class='item-price'>${total_val:.2f}</span></li>"
            except:
                items_list += f"<li>{item.get('description', 'Item')}</li>"
        
        if not items_list:
            items_list = "<li class='no-items'>No items detected</li>"

        # Format total amount
        total_amt = res.get('total_amount')
        try:
            total_display = f"${float(total_amt):,.2f}" if total_amt else "N/A"
        except:
            total_display = str(total_amt) if total_amt else "N/A"

        status = res.get('validation_status') or 'unknown'
        
        rows_html += f"""
        <tr class="invoice-row">
            <td class="row-num">{idx}</td>
            <td class="vendor-cell">{res.get('vendor') or 'Unknown Vendor'}</td>
            <td>{res.get('date') or 'N/A'}</td>
            <td>{res.get('receipt_number') or 'N/A'}</td>
            <td class="total-cell">{total_display}</td>
            <td><ul class="item-list">{items_list}</ul></td>
            <td><span class="badge badge-{status}">{status.title()}</span></td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bulk Invoice Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; 
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            min-height: 100vh;
            padding: 40px 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* Header */
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}
        
        .report-header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .report-header .subtitle {{
            opacity: 0.9;
            font-size: 0.95rem;
        }}
        
        /* Stats Cards */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            text-align: center;
        }}
        
        .stat-card .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #667eea;
        }}
        
        .stat-card .stat-label {{
            font-size: 0.85rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        
        /* Table */
        .table-wrapper {{
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead th {{
            background: #2d3748;
            color: white;
            padding: 16px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        tbody td {{
            padding: 16px 12px;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: top;
        }}
        
        tbody tr:nth-child(even) {{
            background: #f8fafc;
        }}
        
        tbody tr:hover {{
            background: #edf2f7;
        }}
        
        .row-num {{
            color: #a0aec0;
            font-weight: 600;
            width: 50px;
        }}
        
        .vendor-cell {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .total-cell {{
            font-weight: 700;
            color: #38a169;
            font-size: 1.05rem;
        }}
        
        /* Item List */
        .item-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 0.85rem;
        }}
        
        .item-list li {{
            padding: 4px 0;
            color: #4a5568;
            border-bottom: 1px dashed #e2e8f0;
        }}
        
        .item-list li:last-child {{
            border-bottom: none;
        }}
        
        .item-list .item-price {{
            float: right;
            color: #667eea;
            font-weight: 600;
        }}
        
        .item-list .no-items {{
            color: #a0aec0;
            font-style: italic;
        }}
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .badge-passed {{
            background: linear-gradient(135deg, #48bb78, #38a169);
            color: white;
        }}
        
        .badge-failed {{
            background: linear-gradient(135deg, #fc8181, #e53e3e);
            color: white;
        }}
        
        .badge-unknown {{
            background: #e2e8f0;
            color: #4a5568;
        }}
        
        /* Footer */
        .report-footer {{
            text-align: center;
            margin-top: 40px;
            color: #718096;
            font-size: 0.85rem;
        }}
        
        @media print {{
            body {{ background: white; padding: 0; }}
            .report-header {{ box-shadow: none; }}
            .table-wrapper {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>🧾 Bulk Invoice Extraction Report</h1>
            <p class="subtitle">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_invoices}</div>
                <div class="stat-label">Total Invoices</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${total_value:,.2f}</div>
                <div class="stat-label">Total Value</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{passed_count}/{total_invoices}</div>
                <div class="stat-label">Validation Passed</div>
            </div>
        </div>
        
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Vendor</th>
                        <th>Date</th>
                        <th>Invoice #</th>
                        <th>Total</th>
                        <th>Line Items</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <footer class="report-footer">
            <p>Generated by Smart Invoice Processor • Powered by LayoutLMv3 + DocTR</p>
        </footer>
    </div>
</body>
</html>"""
    
    return html_content