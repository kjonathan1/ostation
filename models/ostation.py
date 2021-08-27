# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare


from odoo.addons import decimal_precision as dp

from werkzeug.urls import url_encode

class ostation_jauge(models.Model):
    _name = "ostation.jauge"
    _description = "jauge"
    _sql_constraints = [(
        'name',
        'UNIQUE (idshift,idcuve)',
        'Cette Cuve a déjà été jaugée.'
        )]

    @api.onchange('jaugefin','jaugedebut')
    def verifiermontant(self):
        for rec in self:
            if rec.jaugefin < 0 :
                raise UserError(_("Le Jaugeage de fin doit être supérieur à 0."))
            if rec.jaugedebut < 0 :
                raise UserError(_("Le Jaugeage de debut doit être supérieur à 0."))

    @api.depends('idcuve')
    def getjaugedebut(self):
        for rec in self:
            if rec.idcuve.id != False:
                rec.jaugedebut = self.env['ostation.cuve'].search([('id', '=', str(rec.idcuve.id))])[0].niveaujauge

    
    @api.onchange('idcuve', 'jaugedebut', 'jaugefin')
    def getjaugeecart(self):
        for rec in self:
            rec.ecart = rec.jaugefin - rec.jaugedebut


    jaugedebut = fields.Float(string='Jauge début', compute='getjaugedebut', store=True)
    jaugefin = fields.Float(string='Jauge fin')
    ecart = fields.Float(string='Ecart', compute='getjaugeecart')
    idcuve = fields.Many2one('ostation.cuve', 'Cuve', required=True)
    idshift = fields.Many2one('ostation.shift', 'Shift')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_shift(models.Model):
    _name = "ostation.shift"
    _description = "Shift"
    _sql_constraints = [(
        'name',
        'UNIQUE (date,idtypeshift,idstation)',
        'Ce Shist existe déjà pour cette date.'
        )]
    api.model
    @api.depends('idstation', 'date', 'idtypeshift')
    def getname(self):
        for rec in self:
            rec.name = str(rec.idstation.name) + '/' + str(rec.date) + '/' + str(rec.idtypeshift.name)
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id
            if rec.idtypeshift.id != False: 
                rec.ordershift = rec.idtypeshift.ordre
        
    def getmontant(self):
        for rec in self:
            montantcarburant = montantsolaire = montantrechargegaz = montantconsignegaz = montantaccessoire = montantlubrifiant = montanttotal = ecarttotal = 0
            for record in rec.lignevente:
                montantcarburant += record.montanttotalcarburant
                montantlubrifiant += record.montanttotallubrifiant
                montantaccessoire += record.montanttotalaccessoire
                montantconsignegaz += record.montanttotalconsignegaz
                montantrechargegaz += record.montanttotalrechargegaz
                montantsolaire += record.montanttotalsolaire
                montanttotal += record.montanttotalverse
                ecarttotal += record.ecart
            rec.montantcarburant = montantcarburant
            rec.montantlubrifiant = montantlubrifiant
            rec.montantconsignegaz = montantconsignegaz
            rec.montantrechargegaz = montantrechargegaz
            rec.montantsolaire = montantsolaire
            rec.montantaccessoire = montantaccessoire
            rec.montanttotal = montanttotal
            rec.ecarttotal = ecarttotal
            rec.montanttotaltheorique = montantcarburant + montantsolaire + montantrechargegaz + montantconsignegaz + montantaccessoire + montantlubrifiant
    
    # ecartpompiste   
    def ecartpompiste(self):
        for rec in self:
            for rec2 in rec.lignevente:
                for record in rec2.ligneventedetail:
                    val = {
                            'idemploye': rec2.idemploye.id,
                            'ecart': rec2.ecart,
                            'idshift': rec.id,
                            'state': 'valide',
                            'date': rec.date,
                            'motif': 'VENTE',
                    }
                    self.env['ostation.ecartpompiste'].create(val)
               
     # mise en brouillon ou annulation d'un eecartpompiste: suppression des ligneventedetail
    def suppecartpompiste(self, idshift):
        mouvelines = self.env['ostation.ecartpompiste'].search([('idshift', '=', idshift)])
        mouvelines.unlink()
    
    # mouvement de stocke   
    def mouvementstock(self):
        for rec in self:
            for rec2 in rec.lignevente:
                for record in rec2.ligneventedetail:
                    if record.idarticle.id != False:
                        val = {
                            'idstation': rec.idstation.id,
                            'idarticle': record.idarticle.id,
                            'idcuve' : record.idpistolet.idcuve.id,
                            'idshift': rec.id,
                            'quantiteentree': record.retourcuve,
                            'quantitesortie': record.quantitetheorique,
                            'state': 'valide',
                            'date': rec.date,
                            'type': 'VENTE',
                        }
                        self.env['ostation.mouvementstock'].create(val)
                    else:
                        raise UserError("Veuillez selectionner un article.")
            for record in rec.ligneconsointerne:
                    if record.idarticle.id != False:
                        val = {
                            'idstation': rec.idstation.id,
                            'idarticle': record.idarticle.id,
                            'idcuve' : record.idpistolet.idcuve.id,
                            'idshift': rec.id,
                            'quantiteentree': 0,
                            'quantitesortie': record.quantite,
                            'state': 'valide',
                            'date': rec.date,
                            'type': 'CONSO INTERNE',
                        }
                        self.env['ostation.mouvementstock'].create(val)
                    else:
                        raise UserError("Veuillez selectionner un article.")
            for record in rec.lignerebusstock:
                    if record.idarticle.id != False:
                        val = {
                            'idarticle': record.idarticle.id,
                            'idcuve' : record.idcuve.id,
                            'idshift': rec.id,
                            'quantiteentree': 0,
                            'quantitesortie': record.quantite,
                            'state': 'valide',
                            'date': rec.date,
                            'type': 'REBUS',
                            'motif': record.motif,
                        }
                        self.env['ostation.mouvementstock'].create(val)
                    else:
                        raise UserError("Veuillez selectionner un article.")

    # mise en brouillon ou annulation d'un mouvement de stock: suppression des ligneventedetail
    def suppmouvementstock(self, idshift):
        mouvelines = self.env['ostation.mouvementstock'].search([('idshift', '=', idshift)])
        mouvelines.unlink()

    # Sauvegarde des dernies index des pistolets dans la table pistolet, pour un repositionement au prochain shift
    def sauvegarderindex(self):
        for rec in self:
            tab = []
            for rec2 in rec.lignevente:
                for rec3 in rec2.ligneventedetail:
                    temp = {
                        'indexfin': rec3.indexfin,
                        'idpistolet': rec3.idpistolet.id,
                    }
                    tab.append(temp)
                    
            for pistolet in self.env['ostation.pistolet'].search([('id', '>', 0)]):
                for r2 in tab:
                    if pistolet.id == r2['idpistolet']:
                        pistolet.index = r2['indexfin']
    
    def annulerindex(self):
        for rec in self:
            tab = []
            for rec2 in rec.lignevente:
                for rec3 in rec2.ligneventedetail:
                    temp = {
                        'indexdebut': rec3.indexdebut,
                        'idpistolet': rec3.idpistolet.id,
                    }
                    tab.append(temp)
                    
            for pistolet in self.env['ostation.pistolet'].search([('id', '>', 0)]):
                for r2 in tab:
                    if pistolet.id == r2['idpistolet']:
                        pistolet.index = r2['indexdebut']
    
    def actualiserdernierjauge(self):
        for rec in self:
            for record in rec.lignejauge:
                if record.idcuve.id != False:
                    self.env['ostation.cuve'].search([('id', '=', str(record.idcuve.id))])[0].niveaujauge = record.jaugefin
    
    def annulerdernierjauge(self):
        for rec in self:
            for record in rec.lignejauge:
                if record.idcuve.id != False:
                    self.env['ostation.cuve'].search([('id', '=', str(record.idcuve.id))])[0].niveaujauge = record.jaugedebut

    def valider(self): 
        for rec in self:
            if len(rec.lignejauge) <= 0:
                raise UserError(_("Veuillez saisir les données sur le jaugeage")) 
            dernier_shist = self.env['ostation.shift'].search([('state', '=', 'valide')], order = 'date desc', limit=1 )    
            # raise UserError(_(len(dernier_shist)))
            if len(dernier_shist)>=1: 
                    if rec.date < dernier_shist.date :
                        raise UserError(_("Attention! Date invalide."))
                    if rec.date == dernier_shist.date :
                        if int(dernier_shist.idtypeshift.ordre) > int(rec.idtypeshift.ordre) :
                            raise UserError(_("Attention! Type Shift invalide."))
        
        # nb = len(self.env['ostation.cuve'].search([('idstation','=',str(rec.idstation.id))]))
        # nb1 = len(rec.lignejauge)
        # if nb1 < nb :
        #     raise UserError("Veuillez jauger toutes les cuves!")

        self.actualiserdernierjauge()       
        self.sauvegarderindex()
        self.mouvementstock()
        self.ecartpompiste()
        self.write({'state':'valide'})

    
    def retour(self):
        for rec in self:
            dernier_shist = self.env['ostation.shift'].search([('state', '=', 'valide')], order = 'date desc', limit=1)
            date_dernier_shift = dernier_shist.date
            x = self.env['ostation.shift'].search([('state', '=', 'valide'),('date', '=', date_dernier_shift)])
            # <raise UserError(_(x))
            temp = 0
            last_last = []
            for record in x:
                # raise UserError(_(x.ordershift))
                if int(record.ordershift) > temp:
                    last_last = record

            # raise UserError(_(last_last.name))
            if rec.date == last_last.date and last_last.ordershift <= rec.ordershift:
                # raise UserError(_("on anule"))
                rec.suppmouvementstock(rec.id)
                rec.annulerdernierjauge()
                rec.annulerindex()
                rec.suppecartpompiste(rec.id)
                self.write({'state':'brouillon'})
            else :
                raise UserError(_("Ce shift ne peut pas être mis en brouillon."))

    def annuler(self):
        for rec in self:
            rec.suppmouvementstock(rec.id)
            rec.suppecartpompiste(rec.id)
        self.write({'state':'annuler'})

    
    name = fields.Char(string='Libellé', compute='getname', store=True)
    idstation = fields.Many2one('ostation.station', 'Station')
    date = fields.Date(string='Date', required=True)
    idtypeshift = fields.Many2one('ostation.typeshift', 'Type Shift', required=True)
    ordershift = fields.Float(string='Ordre shift', compute='getname', store=True)
    lignevente = fields.One2many('ostation.lignevente', 'idshift', "Ligne vente article")
    lignenotationemploye = fields.One2many('ostation.notationemploye', 'idshift', "Notation emplyé")
    lignejauge = fields.One2many('ostation.jauge', 'idshift', "Jauge")
    lignerecapgrosclient = fields.One2many('ostation.recapgrosclient', 'idshift', "Consom. gros clients")
    ligneconsointerne = fields.One2many('ostation.consommationinterne', 'idshift', "Consom. interne")
    lignerebusstock = fields.One2many('ostation.rebusstock', 'idshift', "Rebus de stock")

    montantcarburant = fields.Float(string='Total carburant', digits=(16,0), compute='getmontant')
    montantconsignegaz = fields.Float(string='Total consigne gaz', digits=(16,0), compute='getmontant')
    montantrechargegaz = fields.Float(string='Total recharge gaz', digits=(16,0), compute='getmontant')
    montantsolaire = fields.Float(string='Total solaire', digits=(16,0), compute='getmontant')
    montantaccessoire = fields.Float(string='Total accessoire', digits=(16,0), compute='getmontant')
    montantlubrifiant = fields.Float(string='Total lubrifiant', digits=(16,0), compute='getmontant')
    montanttotal = fields.Float(string='Total versé', digits=(16,0), compute='getmontant')
    montanttotaltheorique = fields.Float(string='Total théorique', digits=(16,0), compute='getmontant')
    ecarttotal = fields.Float(string='Total ecart', digits=(16,0), compute='getmontant')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validé'), ('comptabilise','Comptabilisé'),('annuler', ('Annulé'))], string='Etat', default='brouillon')
    etatversementbanque = fields.Selection([('nonverse','Non versé'),('verse','Versé')], string='Versement banque', default='nonverse')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

    idemploye = fields.Many2one('ostation.employe', 'Employé', store=False)
    idpompe = fields.Many2one('ostation.pompe', 'Pompe', store=False)

########################## ligne de vente global ####################

class ostation_lignevente(models.Model):
    _name = "ostation.lignevente"
    _description = "ligne de vente des article"
    _sql_constraints = [(
        'idshiftidemploye',
        'UNIQUE (idshift,idemploye)',
        'La fiche de versement de cet employé existe déjà.'
        ),
        (
        'idshiftidpompe',
        'UNIQUE (idshift,idpompe)',
        'Cette pompe a déjà été selectionnée.'
        )
        ]

    # @api.depends('ligneventedetail')
    # def verifierlignedetail(self):
    #     for rec in self:
    #         for record in rec.ligneventedetail:
    #             raise UserError (str(record.idarticle.id) + ' - '+ str(record.idarticle))
    #             if record.idarticle.id == False:

    #                 raise UserError ("Un article n'a pas été renseigné dans un des fiche Pompiste; veuillez revoir.")

    
    @api.depends('ligneventedetail.montantverser', 'ligneventedetail.montanttheorique')
    def getmontant(self):
        for rec in self:
            montantcarburant = montantlubrifiant= montantsolaire = montantrechargegaz = montantconsignegaz = montantaccessoire= montanttotaltheorique = montanttotalverse = ecart = 0
            for record in rec.ligneventedetail:
                if record.idarticle.idcategoriearticle.name != False:
                    if record.idarticle.idcategoriearticle.type == 'carburant' :
                        montantcarburant += record.montanttheorique
                    if record.idarticle.idcategoriearticle.type == 'lubrifiant':
                        montantlubrifiant += record.montanttheorique
                    if record.idarticle.idcategoriearticle.type == 'consignegaz':
                        montantconsignegaz += record.montanttheorique
                    if record.idarticle.idcategoriearticle.type == 'rechargegaz':
                        montantrechargegaz += record.montanttheorique
                    if record.idarticle.idcategoriearticle.type == 'solaire':
                        montantsolaire += record.montanttheorique
                    if record.idarticle.idcategoriearticle.type == 'accessoire':
                        montantaccessoire += record.montanttheorique
                    montanttotalverse += record.montantverser

            for record in rec.ligneversement:
                if record.idtypepaiement != False:
                    montanttotalverse += record.montant
            rec.montanttotalverse = montanttotalverse
    
            rec.montanttotalcarburant = montantcarburant
            rec.montanttotallubrifiant =  montantlubrifiant
            rec.montanttotalconsignegaz = montantconsignegaz
            rec.montanttotalrechargegaz = montantrechargegaz
            rec.montanttotalsolaire = montantsolaire
            rec.montanttotalaccessoire=montantaccessoire
            rec.montanttotaltheorique=montantcarburant+montantlubrifiant+montantsolaire+montantrechargegaz+montantconsignegaz+montantaccessoire
            
            rec.ecart = rec.montanttotalverse - rec.montanttotaltheorique
    
    @api.depends('idshift')
    def getidstation(self):
        for rec in self:
            rec.idstation = rec.idshift.idstation.id
            rec.id_shift = rec.idshift.id
            

    idshift = fields.Many2one('ostation.shift', 'Shift')
    dateshift = fields.Date('Date shift', related="idshift.date", store=True)  
    idemploye = fields.Many2one('ostation.employe', 'Employé', required=True)
    idpompe = fields.Many2one('ostation.pompe', 'Pompe')   
    montanttotalcarburant = fields.Float("Total carburant", digits=(16,0), compute='getmontant')
    montanttotallubrifiant = fields.Float("Total lubrifiant", digits=(16,0), compute='getmontant')
    montanttotalrechargegaz = fields.Float("Total recharge gaz", digits=(16,0), compute='getmontant')
    montanttotalconsignegaz = fields.Float("Total consigne gaz", digits=(16,0), compute='getmontant')
    montanttotalsolaire = fields.Float("Total Solaire", digits=(16,0), compute='getmontant')
    montanttotalaccessoire = fields.Float("Total accessoire", digits=(16,0), compute='getmontant')
    montanttotaltheorique = fields.Float("Total théorique", digits=(16,0), compute='getmontant')
    montanttotalverse = fields.Float("Total versé", digits=(16,0), compute='getmontant')
    ecart = fields.Float("Ecart", compute='getmontant')
    ligneventedetail = fields.One2many('ostation.ligneventedetail', 'idlignevente', "Ligne vente détails")
    ligneversement = fields.One2many('ostation.ligneversement', 'idlignevente', "Ligne versement")
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default="brouillon", store=True)
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_ligneventedetail(models.Model):
    _name = "ostation.ligneventedetail"
    _description = "ligne de vente des ostation_ligneventedetail article"
    _sql_constraints = [(
        'name',
        'UNIQUE (idlignevente,idpistolet,idarticle)',
        'Vous avez selectionné le même pistolet plus d\'une fois .'
        ),]

    
    @api.onchange('idpistolet')
    def onchange_pistolet_id(self):
        variant_ids_list = []
        
        if self._context.get('idpompetmp'):   #  We will pass this context from the xml view.
            idpompe = self.env["ostation.pompe"].browse(self._context.get('idpompetmp'))
            for variant_id in idpompe.lignepistolet:
                variant_ids_list.append(variant_id.id)
        result = {'domain': {'idpistolet': [('id','in',variant_ids_list)]}}
        return result
    
    
    @api.onchange('retourcuve','idarticle', 'idpistolet', 'indexdebut', 'indexfin','quantitetheorique')
    def getqtevendu(self):
        for rec in self:
            qte = 0
            if rec.indexfin != False:
                if rec.indexdebut <= rec.indexfin:
                    qte = rec.indexfin - rec.indexdebut - rec.retourcuve
                else :
                    raise UserError(_("L'index de fin doit être supérieur à l'index de debut."))

                rec.quantitetheorique = qte


    @api.depends('idarticle', 'idpistolet')
    def getindexdebut(self):
        for rec in self:
            if rec.idpistolet != False:
                for record in self.env['ostation.pistolet'].search([('id', '>', 0)]):
                    if rec.idpistolet.id == record.id :
                        rec.indexdebut = record.index
    
    @api.depends('idarticle', 'quantitetheorique', 'prixunitaire')
    def getmontant(self):
        for rec in self:
            rec.montanttheorique = rec.prixunitaire * rec.quantitetheorique

    @api.onchange('idarticle','prixunitaire')
    def getprixunitaire(self):
        for rec in self:
            rec.prixunitaire = rec.idarticle.prix

    
    
    @api.onchange('retourcuve', 'indexdebut', 'indexfin', 'prixunitaire', 'montantverser', 'quantitetheorique')
    def verifiermontant(self):
        for rec in self:
            if rec.retourcuve < 0 or rec.indexdebut < 0 or rec.indexfin < 0 or rec.prixunitaire < 0 or rec.montantverser < 0 or rec.quantitetheorique < 0 :
                raise UserError(_("Tous les champs doivent comporter une valeur supérieur à 0."))
    
    @api.depends('idarticle')
    def getcategoriearticle(self):
        for rec in self:
            if rec.idarticle != False:
                rec.categoriearticle = rec.idarticle.idcategoriearticle.type

    
    @api.onchange('idpistolet')
    def getarticle(self):
        for rec in self:
            if rec.idpistolet.id != False:
                rec.idarticle = rec.idpistolet.idcuve.idarticle.id
    
    @api.onchange('idarticle', 'idpistolet')
    def getlignearticle(self):
        for rec in self:
            if rec.idpistolet.id == False and rec.categoriearticle == 'carburant':
                raise UserError("Vous devez selectionner le pistolet.")
            if rec.idpistolet.idcuve.idarticle.id != rec.idarticle.id and rec.categoriearticle == 'carburant':
                raise UserError("Pistolet et article non compatibles.")
            if rec.idpistolet.id != False and rec.categoriearticle != 'carburant':
                 raise UserError("Vous ne devez pas selectionner le pistolet pour ce type de produit")



    idlignevente = fields.Many2one('ostation.lignevente', 'Ligne vente')  
    idarticle = fields.Many2one('ostation.article', 'Article', required=True)
    categoriearticle = fields.Char("Libelle categorie article", compute='getcategoriearticle') # ituliser uniquement comme filtre dans le xml
    idpistolet = fields.Many2one('ostation.pistolet', 'Pistolet')
    retourcuve = fields.Float('Retour en cuve', default=0)
    indexdebut = fields.Float('Index debut', compute='getindexdebut', store=True)
    indexfin = fields.Float('Index fin', store=True)
    prixunitaire = fields.Float('Prix unitaire', digits=(16,0))
    quantitetheorique = fields.Float("Quantité")
    montanttheorique = fields.Float("Montant théorique", digits=(16,0), compute='getmontant')
    montantverser = fields.Float("Montant versé", digits=(16,0))
    ecart = fields.Float("Ecart")
    dateshift = fields.Date('Date shift', related="idlignevente.idshift.date", store=True)
    ordreshift = fields.Float('Ordre shift', related="idlignevente.idshift.ordershift", store=True)
    idmouvestock = fields.Many2one('ostation.mouvementstock', 'Mouvement de stock')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', related="idlignevente.idshift.state", store=True)
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_ligneversement(models.Model):
    _name = "ostation.ligneversement"
    _description = "detail sur le type de versement des pompistes"

    def gettotalversement(self):
        t = 0
    
    @api.onchange('montant')
    def verifiermontant(self):
        for rec in self:
            if rec.montant < 0 :
                raise UserError(_("Le Montant versé doit être supérieur à 0."))
    
    idlignevente = fields.Many2one('ostation.lignevente', 'Ligne vente')  
    idtypepaiement = fields.Many2one('ostation.typepaiement', 'Mode paiement')  
    montant = fields.Float("Montant versé", digits=(16,0))
    dateshift = fields.Date('Date shift', related="idlignevente.idshift.date", store=True)
    ordreshift = fields.Float('Ordre shift', related="idlignevente.idshift.ordershift", store=True)
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', related="idlignevente.idshift.state", store=True)
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

########################## fin ligne de vente global ################


################# Lignes des approvisionnements #####################

class ostation_appro(models.Model):
    _name = "ostation.appro"
    _description = "ligne des appro tout article confondu"
    
    @api.depends('idshift')
    def getname(self):
        for rec in self:
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id
            rec.name = "APPRO" + '/' + str(rec.idshift.name)  

    def valider(self):
        for rec in self:
            for record in rec.ligneappro:
                
                val = {
                        'idstation': rec.idstation.id,
                        'idarticle': record.idarticle.id,
                        'idcuve' : record.idcuve.id,
                        'idshift': rec.idshift.id,
                        'quantiteentree': record.quantitelivrer,
                        'quantitesortie': 0 , #record.quantiteretourgaz,
                        'state': 'valide',
                        'date': rec.date,
                        'type': 'APPRO',
                }
                self.env['ostation.mouvementstock'].create(val)
            self.write({'state':'valide'})
               
    
    def suppmouvementstock(self, idshift):
        mouvelines = self.env['ostation.mouvementstock'].search([('idshift', '=', idshift)])
        mouvelines.unlink()

    def retour(self):
        for rec in self:
            rec.suppmouvementstock(rec.id)
        self.write({'state':'brouillon'})

    def annuler(self):
        for rec in self:
            rec.suppmouvementstock(rec.id)
        self.write({'state':'annuler'})
        
    @api.onchange('idsociete')
    def camionparsociete(self):
        for rec in self:
            res = {}
            res['domain'] = {'idcamion':[('idsociete','=',self.idsociete.id)]}
            return res
    
    @api.onchange('idsociete')
    def chauffeurparsociete(self):
        for rec in self:
            res = {}
            res['domain'] = {'idchauffeur':[('idsociete','=',self.idsociete.id)]}
            return res
    
    
            
    
    name = fields.Char('Référence', compute='getname', store=True)
    idstation = fields.Many2one('ostation.station', 'Station', compute='getname', store=True)
    idshift = fields.Many2one('ostation.shift', 'Shift', required=True)
    date = fields.Date(string='Date', required=True)
    idemploye = fields.Many2one('ostation.employe', 'Employé', required=True)
    idcamion = fields.Many2one('ostation.camion', 'Camion', required=True)
    idchauffeur = fields.Many2one('ostation.chauffeur', 'Chauffeur', required=True)
    idsociete = fields.Many2one('ostation.societe', 'Societé de livraison')
    ligneappro = fields.One2many('ostation.ligneappro', 'idappro', "Détails approvisionnements")  
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_ligneappro(models.Model):
    _name = "ostation.ligneappro"
    _description = "ligne de appro des autres article sauf le du carburant"
    _sql_constraints = [(
        'name',
        'UNIQUE (idappro,idcuve,idarticle)',
        'Cet article cuve existe déjà.'
        )]

    @api.onchange('idcuve')
    def getarticle(self):
        for rec in self:
            if rec.idcuve.id != False:
                rec.idarticle = rec.idcuve.idarticle.id
                
    
    @api.onchange('quantitecommander', 'quantitelivrer', 'densitesonabhy', 'densitestation')
    def verifiermontant(self):
        for rec in self:
            if rec.quantitelivrer < 0 or rec.quantitecommander < 0 :
                raise UserError(_("Les Quantités doivent être supérieur à 0."))
            rec.ecart = rec.quantitecommander - rec.quantitelivrer
            rec.ecartdensite = rec.densitestation - rec.densitesonabhy
    
    @api.depends('idarticle')
    def getcategoriearticle(self):
        for rec in self:
            if rec.idarticle != False:
                rec.categoriearticle = rec.idarticle.idcategoriearticle.type

    
    @api.onchange('idarticle', 'idcuve')
    def getlignearticle(self):
        for rec in self:
            if rec.idcuve.id == False and rec.categoriearticle == 'carburant':
                raise UserError("Vous devez selectionner la cuve.")
            if rec.idcuve.idarticle.id != rec.idarticle.id and rec.categoriearticle == 'carburant':
                raise UserError("Cuve et article non compatibles.")
            if rec.idcuve.id != False and rec.categoriearticle != 'carburant':
                raise UserError("Vous ne devez pas selectionner de cuve pour ce type de produit")
    
    
    categoriearticle = fields.Char("Libelle categorie article", compute='getcategoriearticle') # ituliser uniquement comme filtre dans le xml

    idappro = fields.Many2one('ostation.appro', 'Approvisionnement')
    dateappro = fields.Date('Date appro', related="idappro.date", store=True)  
    idarticle = fields.Many2one('ostation.article', 'Article', required=True)
    quantitecommander = fields.Float("Quantité commandée", required=True)
    quantitelivrer = fields.Float("Quantité livrée", required=True)
    quantiteretourgaz = fields.Float("Quantité gaz Retournée")
    densitesonabhy = fields.Float("Densité SONABHY")
    densitestation = fields.Float("Densité STATION")
    ecartdensite = fields.Float("Ecart densité")
    ecart = fields.Float("Ecart quantité")
    idcuve = fields.Many2one('ostation.cuve', 'Cuve')
    idmouvestock = fields.Many2one('ostation.mouvementstock', 'Mouvement de stock')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', related="idappro.state", store=True)
    compartiment = fields.Selection([('1','1'),('2','2'),('3', '3'), ('4', '4'),('5', '5'),('6', '6')], string='compartiment')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

##################

class ostation_minicaisse(models.Model):
    _name = "ostation.minicaisse"
    _description = "Suivi de la mini caisse"
    _sql_constraints = [(
        'name',
        'UNIQUE (name,idstation)',
        'Ce mois existe déjà.'
        )]

    periode_list = [
        ('janvier', 'Janvier'), ('fevrier', 'Février'),('mars', 'Mars'),('avril', 'Avril'),('mai', 'Mai'),('juin', 'Juin'),
        ('juillet', 'Juillet'),('aout', 'Août'),('septembre', 'Septembre'),('octobre', 'Octobre'),('novembre', 'Novembre'),('decembre', 'Décembre'), ]

    @api.onchange('periode', 'date')
    def getname(self):
        for rec in self:
            if rec.date != False:
                rec.name = str(rec.date.strftime("%B").capitalize()) + '-' + str(rec.date.year)

    @api.depends('periode', 'date','lignedepense', 'ligneapprominicaisse')
    def getsolde(self):
        for rec in self:
            resultat=0
            sql =""" SELECT
                    (select sum(a.montant) FROM ostation_approminicaisse a
                    where  EXTRACT(month from a.date) <=%s  and EXTRACT(year from a.date) <=%s)
                    -
                    (select sum(d.montant) FROM ostation_depense d
                    where  EXTRACT(month from d.date) <=%s and EXTRACT(year from d.date) <=%s)
               """
            if rec.date != False:
                # raise UserError(rec.date.strftime("%B"))
                params=(rec.date.month,rec.date.year,rec.date.month,rec.date.year)
                # raise UserError(_(rec.lignedepense.date.month))
                
                for record in rec.lignedepense:
                    if record.date != False: 
                        if record.date.month != rec.date.month:
                            raise UserError(_("Date invalide"))

                for record in rec.ligneapprominicaisse:
                    if record.date != False:
                        if record.date.month != rec.date.month:
                            raise UserError(_("Date invalide"))
                
                self.env.cr.execute(sql,params)              
                resultat=self.env.cr.fetchone()[0]
                if resultat is None:
                    resultat=0
                elif resultat < 0: 
                    raise UserError(_("Le solde de votre mini caisse est insuffisant."))
                
                rec.soldefinal=float(resultat)

    def valider(self):
        self.write({'state':'valide'})

    def retour(self):
        self.write({'state':'brouillon'})

    def annuler(self):
        self.write({'state':'annuler'})
    
    idstation = fields.Many2one('ostation.station', 'Station')
    name = fields.Char(string='Période', compute='getname')
    date = fields.Date(string='Date', required=True)
    periode = fields.Selection(periode_list, string='Periode_2')
    soldefinal = fields.Float(string='Solde mini caisse', digits=(16,0), compute='getsolde', store=True)
    lignedepense = fields.One2many('ostation.depense', 'idminicaisse', 'Dépense')
    ligneapprominicaisse = fields.One2many('ostation.approminicaisse', 'idminicaisse', 'Appro. mini-caisse')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_depense(models.Model):
    _name = "ostation.depense"
    _description = "les depenses"

    @api.onchange('montant')
    def verifiermontant(self):
        for rec in self:
            if rec.montant < 0 :
                raise UserError(_("Le montant doit être supérieur à 0.")) 

    idshift = fields.Many2one('ostation.shift', 'Shift')
    idminicaisse = fields.Many2one('ostation.minicaisse', 'Minicaisse')
    date = fields.Date(string='Date', required=True)
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    name = fields.Char(string='Numéro de reçu')
    date = fields.Date('Date', required=True)  
    description = fields.Char(string='Motif')
    montant = fields.Float(string='Montant', digits=(16,0), required=True)
    idcategoriedepense = fields.Many2one('ostation.categoriedepense', 'Categorie depense')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    idventecarburant = fields.Many2one('ostation.ligneventecarburant', 'depense carburant')

class ostation_approminicaisse(models.Model):
    _name = "ostation.approminicaisse"
    _description = "les approvisionnements de la mini-caisse"

    @api.onchange('montant')
    def verifiermontant(self):
        for rec in self:
            if rec.montant < 0 :
                raise UserError(_("Le montant doit être supérieur à 0.")) 

    idminicaisse = fields.Many2one('ostation.minicaisse', 'Minicaisse')
    date = fields.Date(string='Date', required=True)
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    name = fields.Char(string='libellé')
    montant = fields.Float(string='Montant', digits=(16,0), required=True)
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_recapgrosclient(models.Model):
    _name = "ostation.recapgrosclient"
    _description = "les recapitulatifs de la consommation des gros client par shift"

    
    @api.onchange('quantite', 'prixunitaire')
    def verifiermontant(self):
        for rec in self:
            if rec.prixunitaire < 0 or rec.quantite < 0 :
                raise UserError(_("La Quantité et Prix unitaire doivent être supérieur à 0."))

    @api.onchange('idarticle', 'quantite', 'prixunitaire', 'montant')
    def getmontant(self):
        for rec in self:
            if rec.idarticle.id != False:
                rec.prixunitaire = rec.idarticle.prix
                if rec.quantite != False:
                    rec.montant = rec.prixunitaire * rec.quantite
                if rec.montant != False and rec.prixunitaire != 0:
                    rec.quantite = rec.montant / rec.prixunitaire

    idshift = fields.Many2one('ostation.shift', 'Shift')
    dateshift = fields.Date('Date shift', related="idshift.date", store=True)  
    idclient = fields.Many2one('ostation.client', 'Client')
    idchauffeur = fields.Many2one('ostation.chauffeur', 'Chauffeur')
    idarticle = fields.Many2one('ostation.article', 'Article')
    quantite = fields.Float("Quantité")
    prixunitaire = fields.Float('Prix unitaire', digits=(16,0))
    montant = fields.Float("Montant", digits=(16,0))
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    nbons = fields.Char(string='N° de bon')
    idtypepaiement = fields.Many2one('ostation.typepaiement', 'Mode paiement') 
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', related="idshift.state", store=True)
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    

class ostation_versementbanque(models.Model):
    _name = "ostation.versementbanque"
    _description = "les versements en banque"


    @api.onchange('idbanque', 'shiftids', 'frais')
    def getname(self):
        for rec in self:
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id
            #avoir montanttotal des shifts
            montantshifts = 0
            for record in rec.shiftids:
                montantshifts +=  record.montanttotal
            rec.montantshifts = montantshifts
            rec.montant = rec.montantshifts - rec.frais

    def valider(self): 
        for rec in self:
            if rec.montant < 0:
                raise UserError(_("Le montant doit être supérieur à 0."))
            for record in rec.shiftids:
                record.etatversementbanque = 'verse'

        self.write({'state':'valide'})

    def retour(self):
        self.write({'state':'brouillon'})

    def annuler(self):
        self.write({'state':'annuler'})
    
    idstation = fields.Many2one('ostation.station', 'Station')
    idbanque = fields.Many2one('ostation.banque', 'Banque')
    date = fields.Date('Date', default=fields.Date.today)
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    name = fields.Char(string='N° Bordereau de versement')
    commentaire = fields.Char(string='Commentaire')
    
    shiftids = fields.Many2many('ostation.shift', string="Shifts")
    montantshifts = fields.Float(string='Total Shifts', digits=(16,0))
    frais = fields.Float(string='Frais versement', digits=(16,0))
    montant = fields.Float(string='Montant Versé', digits=(16,0))
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_notationemploye(models.Model):
    _name = "ostation.notationemploye"
    _description = "notation des employe"
    _sql_constraints = [(
        'name',
        'UNIQUE (idshift,idemploye)',
        'Cet employé est déjà noté.'
        )]

    def valider(self): 
        for rec in self:
            if rec.note < 0:
                raise UserError(_("La note doit être supérieur à 0."))

        self.write({'state':'valide'})

    def retour(self):
        self.write({'state':'brouillon'})

    def annuler(self):
        self.write({'state':'annuler'})
    
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    idshift = fields.Many2one('ostation.shift', 'Shift')
    note = fields.Float(string='Note')
    name = fields.Many2one('ostation.criterenotationemploye', 'Critères')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_consommationinterne(models.Model):
    _name = "ostation.consommationinterne"
    _description = "consommation interne"

    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette critère existe déjà.'
        )]
    
    @api.onchange('idpistolet', 'idarticle', 'quantite')
    def getarticle(self):
        for rec in self:
            if rec.idpistolet.id != False:
                rec.idarticle = rec.idpistolet.idcuve.idarticle.id
                rec.prixunitaire = rec.idarticle.prix
                rec.montant = rec.quantite * rec.prixunitaire

    
    @api.onchange('quantite')
    def verifiermontant(self):
        for rec in self:
            if rec.quantite < 0 :
                raise UserError(_("La Quantité doit être supérieur à 0."))
    
    @api.onchange('idpompe')
    def get_pistolet_pompe(self):
        for rec in self:
            return {'domain': {'idpistolet': [('idpompe', '=', rec.idpompe.id)]}}
               
    
    idshift = fields.Many2one('ostation.shift', 'Shift')
    name = fields.Char('Motif')
    date=fields.Date('Date', default=fields.Date.today)
    idpistolet=fields.Many2one('ostation.pistolet','Pistolet')
    idarticle = fields.Many2one('ostation.article', 'Article')
    idpompe = fields.Many2one('ostation.pompe', 'Pompe')
    quantite = fields.Float("Quantité")
    prixunitaire = fields.Float('Prix unitaire', digits=(16,0))
    montant = fields.Float("Montant", digits=(16,0))
    idemploye = fields.Many2one('ostation.employe', 'Employé')
    dateshift = fields.Date('Date shift', related="idshift.date", store=True)
    ordreshift = fields.Float('Ordre shift', related="idshift.ordershift", store=True)
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', related="idshift.state", store=True)
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    

class ostation_criterenotationemploye(models.Model):
    _name = "ostation.criterenotationemploye"
    _description = "critere de notation des employes"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette critère existe déjà.'
        )]

    name = fields.Char(string='Critère de notation')
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_chargerecurente(models.Model):
    _name = "ostation.chargerecurente"
    _description = "suivi des charges recurentes"
    _sql_constraints = [(
        'name',
        'UNIQUE (date,reference)',
        'Cette date et cette reference existent déjà.'
        )]

    @api.depends('name')
    def getname(self):
        for rec in self:
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id

    def soumettre(self):
        self.write({'state':'atraite'})
    def traiter(self):
        self.write({'state':'traite'})
    def retour(self):
        self.write({'state':'brouillon'})
    def annuler(self):
        self.write({'state':'annuler'})

    idstation = fields.Many2one('ostation.station', 'Station', compute='getname')
    name = fields.Char(string='Libellé', required=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    delai = fields.Date(string='Date', default=fields.Date.today, required=True)
    reference = fields.Char(string='Référence utile')
    montant = fields.Float(string='Montant')
    state = fields.Selection([('brouillon','Brouillon'),('atraite','A Traiter'),('traite','Traité'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
   

class ostation_rebusstock(models.Model):
    _name = "ostation.rebusstock"
    _description = "rebus de stock"

    @api.onchange('idpompe')
    def get_pistolet_pompe(self):
        for rec in self:
            rec.idcuve = rec.idpistolet.idcuve.id
            return {'domain': {'idpistolet': [('idpompe', '=', rec.idpompe.id)]}}

    @api.onchange('idpistolet')
    def get_cuve_article(self):
        for rec in self:
            if rec.idpistolet.id != False:
                rec.idarticle = rec.idpistolet.idcuve.idarticle.id
                rec.idcuve = rec.idpistolet.idcuve.id

    idshift = fields.Many2one('ostation.shift', 'Shift')
    idpistolet = fields.Many2one('ostation.pistolet', 'Pistolet')
    idpompe = fields.Many2one('ostation.pompe', 'Pompe')
    idcuve = fields.Many2one('ostation.cuve', 'Cuve')
    idarticle = fields.Many2one('ostation.article', 'Article', required=True)
    quantite = fields.Float("Quantité ")
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    motif = fields.Char(string="Motif", required=True)
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


# class ostation_reglementclient(models.Model):
#     _name = "ostation.reglementclient"
#     _description = "reglement des credit client"

#     idclient = fields.Many2one('ostation.client', 'Client')
#     idtypepaiement = fields.Many2one('ostation.typepaiement', 'Paiement')
#     name = fields.Char(string='Libellé')
#     date = fields.Date('Date')
#     montant = fields.Float('Montant', digits=(16,0))
#     state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
#     synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
