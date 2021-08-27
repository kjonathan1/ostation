# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare


from odoo.addons import decimal_precision as dp

from werkzeug.urls import url_encode




class ostation_societe(models.Model):
    _name = "ostation.societe"
    _description = "societe des chauffeurs de camion"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Société existe déjà.'
        )]
    
   
    name = fields.Char(string='Société', required=True)
    rccm = fields.Char(string='RCCM')
    ifu = fields.Char(string='IFU')
    regime = fields.Char(string='Régime fiscal')
    division = fields.Char(string='Division fiscale')
    adresse = fields.Char(string='Adresse')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codesociete=fields.Char(string='Code société')
    lignecamion=fields.One2many('ostation.camion','idsociete','Camion')
    lignechauffeur=fields.One2many('ostation.chauffeur','idsociete','Chauffeur')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

    

class ostation_chauffeur(models.Model):
    _name = "ostation.chauffeur"
    _description = "chauffeur"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Ce Chauffeur existe déjà.'
        )]

    
    name = fields.Char(string='Chauffeur', required=True)
    nom = fields.Char(string='Nom')
    prenom = fields.Char(string='Prénom(s)')
    cnib = fields.Char(string='CNIB')
    telephone = fields.Char(string='N° de telephone')
    adresse = fields.Char(string='Adresse')
    idsociete = fields.Many2one('ostation.societe','Société')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codechauffeur=fields.Char(string='Code chauffeur')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')    
   



class ostation_camion(models.Model):
    _name = "ostation.camion"
    _description = "camion"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Immatriculation existe déjà.'
        )]

    name = fields.Char(string='Immatriculation', required=True)
    marque = fields.Char(string='Marque')
    capacite = fields.Char(string='Capacité')
    nbcompartiment = fields.Char(string='Nombre de compartiment')
    idsociete = fields.Many2one('ostation.societe','Société')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codecamion=fields.Char(string='Code camion')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    
    
class ostation_typepaiement(models.Model):
    _name = "ostation.typepaiement"
    _description = "typepaiement"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Ce mode de paiement existe déjà.'
        )]

    name = fields.Char(string='Mode versement', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codetypepaiement=fields.Char(string='Code mode paiement')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    
class ostation_article(models.Model):
    _name = "ostation.article"
    _description = "article"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cet article existe déjà.'
        )]

    def getqtedispo(self):
        for rec in self: 
            qte = 0
            for record in self.env['ostation.mouvementstock'].search([('id', '>', 0)]):
                if rec.id == record.idarticle.id:
                    qte += record.quantiteentree - record.quantitesortie
            rec.quantitedisponible = qte

    @api.onchange('idcategoriearticle')
    def gettypearticle (self):
        for rec in self:
            rec.typearticle = rec.idcategoriearticle.type
            # raise UserError(rec.typearticle)

    name = fields.Char(string='Nom', required=True)
    description = fields.Char(string='Description')
    prix = fields.Float(string='Prix de vente', required=True)
    cout = fields.Float(string="Coût d'achat")
    quantitedisponible = fields.Float("Quantité disponible", compute='getqtedispo')
    quantitebouteillevide = fields.Float("Quantité de bouteille vide")
    idcategoriearticle = fields.Many2one('ostation.categoriearticle', 'Categorie article', required=True)
    typearticle = fields.Char('Type article importe')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codearticle=fields.Char(string='Code article')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    

class ostation_categoriearticle(models.Model):
    _name = "ostation.categoriearticle"
    _description = "categorie article"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Catégorie d\'article existe déjà.'
        )]

    name = fields.Char(string='Catégorie d\'article', required=True)
    type=fields.Selection([('carburant', 'CARBURANT'), ('consignegaz', 'CONSIGNE GAZ'),('rechargegaz', 'RECHARGE DE GAZ'),('lubrifiant', 'LUBRIFIANT'),('solaire', 'SOLAIRE'),('accessoire', 'ACCESSOIRES')],string='Type', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codecategoriearticle=fields.Char(string='Code categorie article')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    

class ostation_client(models.Model):
    _name = "ostation.client"
    _description = "Client"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Le nom de ce client existe déjà.'
        )]

    name = fields.Char(string='Client', required=True)
    nom = fields.Char(string='Nom')
    prenom = fields.Char(string='Prénom(s)')
    adresse = fields.Char(string='Adresse')
    idcategorieclient = fields.Many2one('ostation.categorieclient', 'Categorie client')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codeclient=fields.Char(string='Code client')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    
class ostation_categorieclient(models.Model):
    _name = "ostation.categorieclient"
    _description = "categorie client"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Catégorie de client existe déjà.'
        )]
    
    name = fields.Char(string='Catégorie de client', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codecategorieclient=fields.Char(string='Code categorie client')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_employe(models.Model):
    _name = "ostation.employe"
    _description = "Employe"
    _sql_constraints = [(
        'cnib',
        'UNIQUE (cnib)',
        'Ce numéro CNIB/Passport existe déjà.'
        )]

    @api.depends('nom', 'prenom')
    def getname(self):
        for rec in self:
            rec.name = str(rec.nom) + ' ' + str(rec.prenom)

    def getsolde(self):
        for rec in self:
            ecart = reglement = 0
            for rec1 in rec.ligneecart:
                ecart += rec1.ecart
            for rec2 in rec.lignesolde:
                reglement += rec2.montant
            
            rec.ecart =  ecart + reglement
    
    name = fields.Char(string='Employé', compute='getname')
    nom = fields.Char(string='Nom', required=True)
    prenom = fields.Char(string='Prénom(s)', required=True)
    cnib = fields.Char(string='CNIB/Passport', required=True)
    telephone = fields.Char(string='N° de telephone')
    dateembauche=fields.Date(string='Date d\'embauche')
    adresse = fields.Char(string='Adresse')
    ecart = fields.Float('Ecarts en cours ....', compute="getsolde")
    idstation = fields.Many2one('ostation.station', 'Station')
    idcategorieemploye = fields.Many2one('ostation.categorieemploye', 'Catégorie employé', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codeemploye=fields.Char(string='Code employe')
    ligneecart = fields.One2many('ostation.ecartpompiste', 'idemploye', string="Ligne Ecart")
    lignesolde = fields.One2many('ostation.soldepompiste', 'idemploye', string="Ligne Solde")
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

class ostation_categorieemploye(models.Model):
    _name = "ostation.categorieemploye"
    _description = "categorie Employe"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Catégorie d\'employé existe déjà.'
        )]

    name = fields.Char(string='Catégorie employé', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codecategorieemploye=fields.Char(string='Code catégorie employé')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
   

class ostation_station(models.Model):
    _name = "ostation.station"
    _description = "station"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Station de client existe déjà.'
        )]


    def getqtedispo(self):
        t=0

    name = fields.Char(string='Station', required=True)
    orangemoney = fields.Char(string='N° orange money')
    code = fields.Char(string='Code station', required=True)
    adresse = fields.Char(string='Adresse')
    idemploye=fields.Many2one('ostation.employe','Gérant')
    quantitebouteillegaz = fields.Float("Quantité bouteille total", compute='getqtedispo')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
   
    

class ostation_typeshift(models.Model):
    _name = "ostation.typeshift"
    _description = "type de shift"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Le type de shift existent déjà.'
        ),
        (
        'ordre',
        'UNIQUE (ordre)',
        'L\'ordre existent déjà.'
        )]

    name = fields.Char(string='Libellé', required=True)
    ordre = fields.Char(string='Ordre', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    
################# Elements station ###################3

class ostation_pistolet(models.Model):
    _name = "ostation.pistolet"
    _description = "pistolet"
    _sql_constraints = [(
        'name',
        'UNIQUE (name,idpompe)',
        'Cet pistolet existe déjà sur cette pompe.'
        )]

    idpompe = fields.Many2one('ostation.pompe','Pompe')
    idcuve = fields.Many2one('ostation.cuve', 'Cuve', required=True)
    name = fields.Char(string='Libellé', required=True)
    index = fields.Float(string='Dernier index')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codepistolet=fields.Char(string='Code pistolet')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_pompe(models.Model):
    _name = "ostation.pompe"
    _description = "pompe"
    _sql_constraints = [(
        'name',
        'UNIQUE (name,idstation)',
        'Cette Pompe existe déjà dans votre station.'
        )]

    idstation = fields.Many2one('ostation.station', 'Station', required=True)
    name = fields.Char(string='Libellé', required=True)
    marque = fields.Char(string='Marque')
    datedebutservice = fields.Date(string='Mise en service')
    lignepistolet=fields.One2many('ostation.pistolet','idpompe', 'Pistolets')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codepompe=fields.Char(string='Code pompe')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')



class ostation_cuve(models.Model):
    _name = "ostation.cuve"
    _description = "cuve"
    _sql_constraints = [(
        'name',
        'UNIQUE (name,idstation)',
        'Cette Cuve existe déjà dans votre station.'
        )]

    api.model
    @api.depends( 'name')
    def getname(self):
        for rec in self:
            # rec.name = str(rec.idstation.name) + '/' + str(rec.date) + '/' + str(rec.idtypeshift.name)
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id

    def getqtedispo(self):
        for rec in self:
            rec.idstation = self.env['ostation.station'].search([('active', '=', True)])[0].id
            
            qte = 0

            for record in self.env['ostation.mouvementstock'].search([('id', '>', 0)]):
                if rec.id == record.idcuve.id:
                    qte += record.quantiteentree - record.quantitesortie

            rec.quantitedisponible = qte

    idstation = fields.Many2one('ostation.station', 'Station', compute='getname')
    name = fields.Char(string='Libellé', required=True)
    capacite = fields.Char(string='Capacité', required=True)
    idarticle = fields.Many2one('ostation.article', 'Article', required=True )
    quantitedisponible = fields.Float("Quantité disponible", compute='getqtedispo')
    niveaujauge = fields.Float(string='Dernière jauge')
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codecuve=fields.Char(string='Code cuve')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
    
    
class ostation_categoriedepense(models.Model):
    _name = "ostation.categoriedepense"
    _description = "categorie depense"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Catégorie de depense existe déjà.'
        )]

    name = fields.Char(string='Catégorie depense', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
   
class ostation_banque(models.Model):
    _name = "ostation.banque"
    _description = "Banque"
    _sql_constraints = [(
        'name',
        'UNIQUE (name)',
        'Cette Banque existe déjà.'
        )]

    name = fields.Char(string='Banque', required=True)
    active = fields.Boolean(default=True, string='Actif', help="Définissez Actif sur false pour masquer la balise de l'objet sans la supprimer")
    codebanque=fields.Char(string='Code banque')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')
   

class ostation_mouvementstock(models.Model):
    _name = "ostation.mouvementstock"
    _description = "mouvementstock"

    idstation = fields.Many2one('ostation.station', 'Station')
    idshift = fields.Many2one('ostation.shift', 'Shift')
    idcuve = fields.Many2one('ostation.cuve', 'Cuve')
    idarticle = fields.Many2one('ostation.article', 'Article')
    quantiteentree = fields.Float("Quantité entrée")
    quantitesortie = fields.Float("Quantité sortie")
    date = fields.Date(string='Date')
    type = fields.Char(string="Type d'opération")
    motif = fields.Char(string="Motif")
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_ecartpompiste(models.Model):
    _name = "ostation.ecartpompiste"
    _description = "ecart des pompistes"

    idshift = fields.Many2one('ostation.shift', 'Shift')
    idemploye = fields.Many2one('ostation.employe','Employé')
    ecart = fields.Float("Ecart")
    date = fields.Date(string='Date')
    motif = fields.Char(string="Motif")
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')


class ostation_soldepompiste(models.Model):
    _name = "ostation.soldepompiste"
    _description = "solde des pompistes"

    idemploye = fields.Many2one('ostation.employe','Employé')
    date = fields.Date(string='Date')
    montant = fields.Float("Montant")
    motif = fields.Char(string="Motif")
    state = fields.Selection([('brouillon','Brouillon'),('valide','Validée'),('annuler', ('Annuler'))], string='Etat', default='brouillon')
    synccode = fields.Selection([('0', 'Non sychronise'), ('1', 'modifier'), ('2', 'sychronise')], default='0')

