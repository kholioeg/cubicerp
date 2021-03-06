# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields,osv
import openerp.addons.decimal_precision as dp

class account_entries_report(osv.osv):
    _name = "account.entries.report"
    _description = "Journal Items Analysis"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Effective Date', readonly=True),  # TDE FIXME master: rename into date_effective
        'date_created': fields.date('Date Created', readonly=True),
        'date_maturity': fields.date('Date Maturity', readonly=True),
        'ref': fields.char('Reference', readonly=True),
        'note': fields.char('Note', readonly=True),
        'nbr': fields.integer('# of Items', readonly=True),
        'debit': fields.float('Debit', readonly=True),
        'credit': fields.float('Credit', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'amount_currency': fields.float('Amount Currency', digits_compute=dp.get_precision('Account'), readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'account_id': fields.many2one('account.account', 'Account', readonly=True),
        'parent_account_id': fields.many2one('account.account', 'Parent Account', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure', readonly=True),
        'move_state': fields.selection([('draft','Unposted'), ('posted','Posted')], 'Status', readonly=True),
        'move_line_state': fields.selection([('draft','Unbalanced'), ('valid','Valid')], 'State of Move Line', readonly=True),
        'reconcile_id': fields.many2one('account.move.reconcile', 'Reconciliation number', readonly=True),
        'partner_id': fields.many2one('res.partner','Partner', readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'analytic_parent_id': fields.many2one('account.analytic.account', 'Analytic Parent Account', readonly=True),
        'quantity': fields.float('Products Quantity', digits=(16,2), readonly=True),  # TDE FIXME master: rename into product_quantity
        'user_type': fields.many2one('account.account.type', 'Account Type', readonly=True),
        'report_type': fields.many2one('account.financial.report', 'Financial Report', readonly=True),
        'chart_account': fields.many2one('account.account', 'Chart Account', readonly=True),
        'type': fields.selection([
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('cash', 'Cash'),
            ('view', 'View'),
            ('consolidation', 'Consolidation'),
            ('other', 'Regular'),
            ('closed', 'Closed'),
        ], 'Internal Type', readonly=True, help="This type is used to differentiate types with "\
            "special effects in Odoo: view can not have entries, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    _order = 'date desc'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        for arg in args:
            if arg[0] == 'period_id' and arg[2] == 'current_period':
                current_period = period_obj.find(cr, uid, context=context)[0]
                args.append(['period_id','in',[current_period]])
                break
            elif arg[0] == 'period_id' and arg[2] == 'current_year':
                current_year = fiscalyear_obj.find(cr, uid)
                ids = fiscalyear_obj.read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
                args.append(['period_id','in',ids])
        for a in [['period_id','in','current_year'], ['period_id','in','current_period']]:
            if a in args:
                args.remove(a)
        return super(account_entries_report, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
            context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,lazy=True):
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        if context.get('period', False) == 'current_period':
            current_period = period_obj.find(cr, uid, context=context)[0]
            domain.append(['period_id','in',[current_period]])
        elif context.get('year', False) == 'current_year':
            current_year = fiscalyear_obj.find(cr, uid)
            ids = fiscalyear_obj.read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
            domain.append(['period_id','in',ids])
        else:
            domain = domain
        return super(account_entries_report, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby,lazy)

    def _get_select(self):
        return ''

    def _get_from(self):
        return ''

    def _get_where(self):
        return ''

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_entries_report')
        cr.execute("""
            create or replace view account_entries_report as (
            select
                l.id as id,
                am.date as date,
                l.date_maturity as date_maturity,
                l.date_created as date_created,
                am.ref as ref,
                l.name as note,
                am.state as move_state,
                l.state as move_line_state,
                l.reconcile_id as reconcile_id,
                l.partner_id as partner_id,
                l.product_id as product_id,
                l.product_uom_id as product_uom_id,
                am.company_id as company_id,
                am.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                am.period_id as period_id,
                l.account_id as account_id,
                a.parent_id as parent_account_id,
                l.analytic_account_id as analytic_account_id,
                aaa.parent_id as analytic_parent_id,
                a.type as type,
                a.user_type as user_type,
                at.financial_report_id as report_type,
                a.chart_account_id as chart_account,
                1 as nbr,
                l.quantity as quantity,
                l.currency_id as currency_id,
                l.amount_currency as amount_currency,
                l.debit as debit,
                l.credit as credit,
                coalesce(l.debit, 0.0) - coalesce(l.credit, 0.0) as balance
                %s
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_account_type at on (a.user_type = at.id)
                left join account_move am on (am.id=l.move_id)
                left join account_period p on (am.period_id=p.id)
                left join account_analytic_account aaa on (l.analytic_account_id = aaa.id)
                %s
                where l.state != 'draft'
                %s
            )
        """%(self._get_select(),self._get_from(),self._get_where()))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
