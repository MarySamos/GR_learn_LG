"""
报告生成服务
使用 ReportLab 生成 PDF 报告
"""
import io
from datetime import datetime
from typing import Dict, Any

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ReportService:
    """PDF 报告生成服务"""
    
    def __init__(self):
        self.styles = None
        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
    
    def generate_analysis_report(self, data: Dict[str, Any]) -> bytes:
        """
        生成数据分析报告 PDF
        
        Args:
            data: 分析数据字典，包含 statistics, quality, clustering 等
        
        Returns:
            PDF 文件字节
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab 未安装，请运行: pip install reportlab")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)
        
        elements = []
        
        # 标题
        title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Z-Rop - Data Analysis Report", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.styles['Normal']))
        elements.append(Spacer(1, 30))
        
        # 数据概览
        if 'quality' in data:
            q = data['quality']
            elements.append(Paragraph("1. Data Overview", self.styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            overview_data = [
                ['Metric', 'Value'],
                ['Total Rows', str(q.get('total_rows', 'N/A'))],
                ['Total Columns', str(q.get('total_columns', 'N/A'))],
                ['Completeness', f"{q.get('completeness', 0)}%"],
                ['Missing Cells', str(q.get('total_missing_cells', 0))]
            ]
            
            table = Table(overview_data, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0071E3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F7')),
                ('GRID', (0, 0), (-1, -1), 1, colors.white)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 30))
        
        # 统计分析
        if 'statistics' in data:
            elements.append(Paragraph("2. Descriptive Statistics", self.styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            stats = data['statistics'].get('statistics', {})
            if stats:
                header = ['Column', 'Mean', 'Median', 'Std Dev', 'Min', 'Max']
                rows = [header]
                
                for col, s in list(stats.items())[:10]:
                    rows.append([
                        col,
                        str(s.get('mean', 'N/A')),
                        str(s.get('median', 'N/A')),
                        str(s.get('std', 'N/A')),
                        str(s.get('min', 'N/A')),
                        str(s.get('max', 'N/A'))
                    ])
                
                table = Table(rows, colWidths=[80, 70, 70, 70, 70, 70])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34C759')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F7')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.white)
                ]))
                elements.append(table)
            elements.append(Spacer(1, 30))
        
        # 聚类分析
        if 'clustering' in data:
            elements.append(Paragraph("3. Customer Segmentation", self.styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            c = data['clustering']
            elements.append(Paragraph(f"Number of Clusters: {c.get('n_clusters', 'N/A')}", self.styles['Normal']))
            elements.append(Paragraph(f"Silhouette Score: {c.get('silhouette_score', 'N/A')}", self.styles['Normal']))
            elements.append(Spacer(1, 15))
            
            profiles = c.get('cluster_profiles', [])
            if profiles:
                header = ['Cluster', 'Size', 'Percentage', 'Conversion Rate', 'Label']
                rows = [header]
                
                for p in profiles:
                    rows.append([
                        str(p.get('cluster_id', '')),
                        str(p.get('size', '')),
                        f"{p.get('percentage', 0)}%",
                        f"{p.get('conversion_rate', 0)}%",
                        p.get('label', '')[:20]
                    ])
                
                table = Table(rows, colWidths=[50, 60, 70, 90, 150])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AF52DE')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F7')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.white)
                ]))
                elements.append(table)
        
        # 生成 PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# 全局服务实例
report_service = ReportService()
