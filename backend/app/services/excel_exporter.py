"""
Excel导出服务 - 生成Excel格式报价单
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import logging
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from app.models.quote import QuoteSheet, QuoteItem
from app.services.oss_uploader import get_oss_uploader

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Excel导出器"""
    
    def __init__(self):
        self.title_font = Font(name='微软雅黑', size=16, bold=True)
        self.header_font = Font(name='微软雅黑', size=11, bold=True, color="FFFFFF")
        self.normal_font = Font(name='微软雅黑', size=10)
        
        self.header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        self.total_fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        
        self.thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    async def generate_standard_quote(
        self,
        quote: QuoteSheet,
        items: List[QuoteItem]
    ) -> bytes:
        """
        生成标准报价单
        
        Args:
            quote: 报价单主记录
            items: 报价明细列表
        
        Returns:
            Excel文件字节流
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "报价单"
        
        # 设置列宽
        column_widths = {
            'A': 5,   # 序号
            'B': 25,  # 产品名称
            'C': 20,  # 规格配置
            'D': 10,  # 数量
            'E': 10,  # 时长
            'F': 15,  # 单价
            'G': 15,  # 小计
            'H': 20   # 备注
        }
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
        
        # 1. 标题部分
        current_row = 1
        ws.merge_cells(f'A{current_row}:H{current_row}')
        title_cell = ws[f'A{current_row}']
        title_cell.value = "阿里云产品报价单"
        title_cell.font = self.title_font
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        current_row += 2
        
        # 2. 基本信息
        info_data = [
            ['客户名称', quote.customer_name, '项目名称', quote.project_name or '-'],
            ['报价日期', quote.created_at.strftime('%Y-%m-%d'), '有效期至', 
             quote.valid_until.strftime('%Y-%m-%d') if quote.valid_until else '-'],
            ['币种', quote.currency, '报价单号', str(quote.quote_id)[:8].upper()]
        ]
        
        for row_data in info_data:
            ws[f'A{current_row}'] = row_data[0]
            ws[f'A{current_row}'].font = Font(bold=True)
            ws[f'B{current_row}'] = row_data[1]
            ws[f'D{current_row}'] = row_data[2]
            ws[f'D{current_row}'].font = Font(bold=True)
            ws[f'E{current_row}'] = row_data[3]
            current_row += 1
        
        current_row += 1
        
        # 3. 表头
        headers = ['序号', '产品名称', '规格配置', '数量', '时长(月)', '单价(元)', '小计(元)', '备注']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.value = header
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.thin_border
        
        current_row += 1
        data_start_row = current_row
        
        # 4. 数据行
        for idx, item in enumerate(items, 1):
            # 序号
            ws.cell(row=current_row, column=1, value=idx)
            ws.cell(row=current_row, column=1).alignment = Alignment(horizontal='center')
            
            # 产品名称
            ws.cell(row=current_row, column=2, value=item.product_name)
            
            # 规格配置
            spec_text = self._format_spec_config(item.spec_config)
            ws.cell(row=current_row, column=3, value=spec_text)
            
            # 数量
            ws.cell(row=current_row, column=4, value=item.quantity)
            ws.cell(row=current_row, column=4).alignment = Alignment(horizontal='center')
            
            # 时长
            ws.cell(row=current_row, column=5, value=item.duration_months or '-')
            ws.cell(row=current_row, column=5).alignment = Alignment(horizontal='center')
            
            # 单价
            ws.cell(row=current_row, column=6, value=float(item.unit_price))
            ws.cell(row=current_row, column=6).number_format = '#,##0.00'
            
            # 小计
            ws.cell(row=current_row, column=7, value=float(item.subtotal))
            ws.cell(row=current_row, column=7).number_format = '#,##0.00'
            
            # 备注(折扣信息)
            remark = self._format_discount_info(item.discount_info)
            ws.cell(row=current_row, column=8, value=remark)
            
            # 应用边框
            for col_idx in range(1, 9):
                ws.cell(row=current_row, column=col_idx).border = self.thin_border
            
            current_row += 1
        
        # 5. 合计行
        ws.merge_cells(f'A{current_row}:F{current_row}')
        total_cell = ws[f'A{current_row}']
        total_cell.value = "报价总计"
        total_cell.font = Font(bold=True, size=11)
        total_cell.alignment = Alignment(horizontal='right', vertical='center')
        total_cell.fill = self.total_fill
        
        total_amount_cell = ws.cell(row=current_row, column=7)
        total_amount_cell.value = float(quote.total_amount)
        total_amount_cell.number_format = '#,##0.00'
        total_amount_cell.font = Font(bold=True, size=11)
        total_amount_cell.fill = self.total_fill
        
        # 应用边框
        for col_idx in range(1, 9):
            ws.cell(row=current_row, column=col_idx).border = self.thin_border
        
        current_row += 2
        
        # 6. 备注说明
        ws.merge_cells(f'A{current_row}:H{current_row}')
        note_cell = ws[f'A{current_row}']
        note_cell.value = "备注: 1. 以上价格为估算价格,实际价格以阿里云官网为准 2. 本报价单有效期30天"
        note_cell.font = Font(size=9, italic=True, color="808080")
        current_row += 1
        
        ws.merge_cells(f'A{current_row}:H{current_row}')
        contact_cell = ws[f'A{current_row}']
        contact_cell.value = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 报价侠系统"
        contact_cell.font = Font(size=9, italic=True, color="808080")
        
        # 转换为字节流
        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def _format_spec_config(self, spec_config: Optional[Dict[str, Any]]) -> str:
        """格式化规格配置"""
        if not spec_config:
            return "-"
        
        parts = []
        for key, value in spec_config.items():
            if key in ['region', 'spec_type', 'billing_mode']:
                continue
            parts.append(f"{key}: {value}")
        
        return "\n".join(parts) if parts else "-"
    
    def _format_discount_info(self, discount_info: Optional[Dict[str, Any]]) -> str:
        """格式化折扣信息"""
        if not discount_info or not discount_info.get('discounts'):
            return "-"
        
        discounts = discount_info.get('discounts', [])
        parts = []
        for discount in discounts:
            discount_type = discount.get('type', '')
            value = discount.get('value', 0)
            
            if discount_type == 'tiered':
                parts.append(f"阶梯折扣: {value}折")
            elif discount_type == 'batch':
                parts.append(f"Batch折扣: {value}折")
            elif discount_type == 'thinking_mode':
                parts.append(f"思考模式: {value}倍")
            elif discount_type == 'package':
                parts.append("套餐价格")
        
        return "\n".join(parts) if parts else "-"
    
    async def generate_competitor_comparison(
        self,
        quote: QuoteSheet,
        items: List[QuoteItem],
        competitor_data: Dict[str, Any]
    ) -> bytes:
        """
        生成竞品对比版报价单
        
        Args:
            quote: 报价单主记录
            items: 报价明细列表
            competitor_data: 竞品数据
        
        Returns:
            Excel文件字节流
        """
        # 竞品对比版本可以后续实现
        # 目前先返回标准版本
        return await self.generate_standard_quote(quote, items)
    
    async def generate_simplified_quote(
        self,
        quote: QuoteSheet,
        items: List[QuoteItem]
    ) -> bytes:
        """
        生成简化版报价单
        
        Args:
            quote: 报价单主记录
            items: 报价明细列表
        
        Returns:
            Excel文件字节流
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "简化报价单"
        
        # 设置列宽
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
        
        # 标题
        ws['A1'] = "产品名称"
        ws['B1'] = "数量"
        ws['C1'] = "价格(元)"
        
        # 应用样式
        for col in ['A', 'B', 'C']:
            cell = ws[f'{col}1']
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # 数据行
        row = 2
        for item in items:
            ws.cell(row=row, column=1, value=item.product_name)
            ws.cell(row=row, column=2, value=item.quantity)
            ws.cell(row=row, column=3, value=float(item.subtotal))
            ws.cell(row=row, column=3).number_format = '#,##0.00'
            row += 1
        
        # 合计
        ws.cell(row=row, column=1, value="总计")
        ws.cell(row=row, column=1).font = Font(bold=True)
        ws.cell(row=row, column=3, value=float(quote.total_amount))
        ws.cell(row=row, column=3).number_format = '#,##0.00'
        ws.cell(row=row, column=3).font = Font(bold=True)
        
        # 转换为字节流
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def generate_and_upload(
        self,
        quote: QuoteSheet,
        items: List[QuoteItem],
        template_type: str = "standard"
    ) -> Tuple[bytes, Optional[str]]:
        """
        生成Excel并上传到OSS
        
        Args:
            quote: 报价单主记录
            items: 报价明细列表
            template_type: 模板类型 (standard/simplified/competitor)
        
        Returns:
            Tuple[bytes, Optional[str]]: (Excel文件字节流, OSS下载URL)
        """
        # 根据模板类型生成Excel
        if template_type == "simplified":
            excel_bytes = await self.generate_simplified_quote(quote, items)
        elif template_type == "competitor":
            excel_bytes = await self.generate_competitor_comparison(quote, items, {})
        else:
            excel_bytes = await self.generate_standard_quote(quote, items)
        
        # 上传到OSS
        oss_url = None
        try:
            uploader = get_oss_uploader()
            oss_url = await uploader.upload_quote_file(
                file_content=excel_bytes,
                quote_id=str(quote.quote_id),
                file_type="xlsx"
            )
            if oss_url:
                logger.info(f"报价单Excel已上传: {oss_url}")
            else:
                logger.warning("报价单Excel上传失败，OSS可能未配置")
        except Exception as e:
            logger.error(f"上传报价单Excel异常: {e}")
        
        return excel_bytes, oss_url
    
    async def batch_export(
        self,
        quotes_data: List[Tuple[QuoteSheet, List[QuoteItem]]],
        template_type: str = "standard",
        upload_to_oss: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量导出报价单
        
        Args:
            quotes_data: 报价单数据列表 [(quote, items), ...]
            template_type: 模板类型
            upload_to_oss: 是否上传到OSS
        
        Returns:
            导出结果列表
        """
        results = []
        
        for quote, items in quotes_data:
            try:
                if upload_to_oss:
                    excel_bytes, oss_url = await self.generate_and_upload(
                        quote, items, template_type
                    )
                    results.append({
                        "quote_id": str(quote.quote_id),
                        "quote_no": quote.quote_no,
                        "success": True,
                        "oss_url": oss_url,
                        "file_size": len(excel_bytes)
                    })
                else:
                    if template_type == "simplified":
                        excel_bytes = await self.generate_simplified_quote(quote, items)
                    else:
                        excel_bytes = await self.generate_standard_quote(quote, items)
                    
                    results.append({
                        "quote_id": str(quote.quote_id),
                        "quote_no": quote.quote_no,
                        "success": True,
                        "file_size": len(excel_bytes)
                    })
            except Exception as e:
                logger.error(f"导出报价单 {quote.quote_no} 失败: {e}")
                results.append({
                    "quote_id": str(quote.quote_id),
                    "quote_no": quote.quote_no,
                    "success": False,
                    "error": str(e)
                })
        
        return results


# 全局导出器实例
_exporter: Optional[ExcelExporter] = None


def get_excel_exporter() -> ExcelExporter:
    """获取Excel导出器实例"""
    global _exporter
    if _exporter is None:
        _exporter = ExcelExporter()
    return _exporter
