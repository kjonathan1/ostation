# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ostation_etat(models.TransientModel):
    _name = "ostation.etat"
    _description = "Etats"

    debut = fields.Date(string="Date de debut", required=True)
    fin = fields.Date(string="Date de fin", required=True)
    idstation = fields.Many2one('ostation.station', 'Station')
    
    def shift_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.reportshist_id').report_action(self, data=data)
    
    def appro_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.reportappro_id').report_action(self, data=data)
    
    def venteperiodique_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.1ventejournalier_id').report_action(self, data=data)
    
    def recette_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.2recette_id').report_action(self, data=data)
    
    def mvtrechargegaz_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.3mvtrechargegaz_id').report_action(self, data=data)

    def bon_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.9bondecarburant_id').report_action(self, data=data)

    def appro_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.7approvisionnement_id').report_action(self, data=data)


    def generate_report(self):
        raise UserError("Fontionalité en cours de developpement.")
    
    def mvtaccessoiregaz_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.5mvtaccessoiregaz_id').report_action(self, data=data)


    def mvtconsignegaz_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.4mvtconsignegaz_id').report_action(self, data=data)
    
    def mvtlubrifiant_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.10mvtlubrifiant_id').report_action(self, data=data)
    
    def mvtsolaire_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.11mvtsolaire_id').report_action(self, data=data)
    
    def global_report(self):
        data = {'debut': self.debut, 'fin': self.fin , 'idstation': self.idstation.id}
        return self.env.ref('ostation.12global_id').report_action(self, data=data)


class ostation_abstractetat(models.AbstractModel):
    _name = 'report.ostation.reportshift_template'
    def _get_report_values(self, docids, data=None):
        domain = [('state', '=', 'valide'), ('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
        docs = []
        for rec in self.env['ostation.shift'].search(domain):
            val = {
                'name': rec.name,
                'date': rec.date.strftime("%m/%d/%Y"),
                'montantcarburant': rec.montantcarburant,
                'montantlubrifiant': rec.montantlubrifiant,
                'montantconsignegaz': rec.montantconsignegaz,
                'montantrechargegaz': rec.montantrechargegaz,
                'montantsolaire': rec.montantsolaire,
                'montantaccessoire': rec.montantaccessoire,
                'montanttotaltheorique': rec.montanttotaltheorique,
                'montanttotal': rec.montanttotal,
                'ecarttotal': rec.ecarttotal,
            }
            docs.append(val)
        return {
            'doc_model': 'ostation.shift',
            'docs': docs,
            'data': data
        }

class ostation_abstractetatappro(models.AbstractModel):
    _name = 'report.ostation.7approvisionnement'
    def _get_report_values(self, docids, data=None):
        domain = []
        if data.get('idstation'):
            domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('state', '=', 'valide'), ('idstation', '=', data.get('idstation'))]
        else :
            domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('state', '=', 'valide'),]  
    
        appros = []
        articles = []
        for rec in self.env['ostation.appro'].search(domain):
            # raise UserError(rec.id)
            for record in self.env['ostation.ligneappro'].search([('idappro', '=', rec.id)]):
                if record.idarticle.id:
                    if 'carburant' in record.idarticle.idcategoriearticle.type:
                
                        val = {
                            'idstation': rec.idstation.id,
                            'date': rec.date.strftime("%d/%m/%Y"),
                            'chauffeur': rec.idchauffeur.name,
                            'immatrivulation': rec.idcamion.name,
                            'capasite': rec.idcamion.capacite,
                            'article': record.idarticle.name,
                            'compartiment': record.compartiment,
                            'temperature': 0,
                            'densite': record.densitestation,
                            'densite_15c': 0,
                            'densite_sonabhy': record.densitesonabhy,
                            'ecartdensite': record.ecartdensite,
                            'quantite_commander': record.quantitecommander,
                            'quantite_livrer': record.quantitelivrer,
                            'ecartquantite': record.quantitecommander - record.quantitelivrer,
                        }
                        appros.append(val)
        return {
            'appros': appros,
            'data': data
        }


class ostation_abstractetatmouvementrechargegaz(models.AbstractModel):
    _name = 'report.ostation.3mvtrechargegaz'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
        resultats = []
        sql_rechargegaz = """
            select  a.name, a.prix ,sum(quantiteentree) as Entre, sum(quantitesortie) as Sortie
            from ostation_mouvementstock m, ostation_article a, ostation_categoriearticle c
            where a.id = m.idarticle 
                and m.date between %s and %s
                and c.id = a.idcategoriearticle
                and c.type like 'rechargegaz'
            Group by a.id
        """
        params = ( data.get('debut'),  data.get('fin'))
        self.env.cr.execute(sql_rechargegaz ,params)
        resultats = self.env.cr.dictfetchall()

        mouvementstock=[]
        stockouv = entree = sortie  = bvstockouv = bvstockfinal = 0

        for r in self.env['ostation.article'].search([]):
            if r.idcategoriearticle.type == 'rechargegaz' :
                stockouv  = sum(m.quantiteentree - m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                entree  = sum(m.quantiteentree  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                sortie = sum(m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                bvstockouv  = r.quantitebouteillevide -  sum(m.quantiteentree + m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                bvstockfinal = bvstockouv + sortie - entree
                # raise UserError(bvstockouv)
                val_mouv = {
                            'name':r.name, 
                            'prix':r.prix,
                            'entree': entree,
                            'sortie':sortie,
                            'stockfinal':stockouv+entree-sortie,
                            'ouverture':stockouv,
                            'valeurvente':sortie*r.prix,
                            'valeurstock':(stockouv+entree-sortie)*r.prix,
                            'bvstockouv': bvstockouv,
                            'bvstockfinal': bvstockfinal,
                }
                mouvementstock.append(val_mouv)
        
        # raise UserError(resultats)
        return {
            
            'mouvementstock': mouvementstock,
            'data': data
        }
class ostation_abstractetatventeperiodique(models.AbstractModel):
    _name = 'report.ostation.1ventejournalier'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
    
        cuves = []
        articles = []
        pistolets = []
        index_fermeture = []
        index_ouverture = []
        sortie = []
        retourcuve = []
        ouvertures_su = []
        ouvertures_ga = []

        for rec in self.env['ostation.cuve'].search([]):
            for record in self.env['ostation.pistolet'].search([('idcuve', '=', rec.id)]):                
                val1 = {
                    'idpistolet': record.id,
                    'name': record.name,
                }
                pistolets.append(val1)
            
            val2 = {
                'name': rec.name,
                'capacite': rec.capacite,
                'pistolet': pistolets,
            }
            cuves.append(val2)
            # raise UserError(pistolets)
            pistolets = []
        
        for rec in self.env['ostation.pistolet'].search([]):
            retourcuve = qtevaleur = ventevaleur = sortie = 0
            indexdebut = 0
            indexfin = 0
            
            for record in self.env['ostation.ligneventedetail'].search([('dateshift', '>=', data.get('debut')), ('dateshift', '<=', data.get('fin')), ('idpistolet', '=', rec.id), ('state', '=', 'valide')], order = 'dateshift asc, ordreshift asc'):
                retourcuve += record.retourcuve 
                qtevaleur += record.quantitetheorique
                ventevaleur += record.montanttheorique
                indexfin = record.indexfin
                   
                if indexdebut == 0:
                    indexdebut= record.indexdebut
                    
            if indexdebut == 0 :
                for record in self.env['ostation.ligneventedetail'].search([('dateshift', '<=', data.get('debut')), ('idpistolet', '=', rec.id), ('state', '=', 'valide')], order = 'dateshift desc, ordreshift desc'):
                    if indexdebut == 0:
                        indexdebut = indexfin = record.indexfin
            # raise UserError(rec.idcuve.idarticle.name.lower())
            if rec.idcuve.id: 
                if 'ga' in rec.idcuve.idarticle.name.lower():
                    ouvertures_ga.append({
                        'cuve': rec.idcuve.name,
                        'idpistolet' : rec.id,
                        'nompistolet' : rec.name,
                        'indexdebut' : indexdebut,
                        'indexfin' : indexfin,
                        'retourcuve' : retourcuve,
                        'qtevaleur' : qtevaleur,
                        'ventevaleur' : ventevaleur,
                        'sortie': indexfin - indexdebut
                    })
            if rec.idcuve.id:
                if 'sup' in rec.idcuve.idarticle.name.lower():
                        ouvertures_su.append({
                        'cuve': rec.idcuve.name,
                        'idpistolet' : rec.id,
                        'nompistolet' : rec.name,
                        'indexdebut' : indexdebut,
                        'indexfin' : indexfin,
                        'retourcuve' : retourcuve,
                        'qtevaleur' : qtevaleur,
                        'ventevaleur' : ventevaleur,
                        'sortie': indexfin - indexdebut
                    })

        # raise UserError(ouvertures)

        return {
            
            'cuves': cuves,
            'data': data,
            'ouvertures_su': ouvertures_su,
            'ouvertures_ga': ouvertures_ga
        }

class ostation_abstractetatrecette(models.AbstractModel):
    _name = 'report.ostation.2recette'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
    
        super = []
        gasoil = []
        volume_su = 0
        prixunitaire_su = 0
        valeur_su = 0
        volume_ga = 0
        prixunitaire_ga = 0
        valeur_ga = 0
        valeur_lubrifiant = 0
        valeur_gaz = 0
        valeur_bon = 0
        ecart_pompiste = 0
        valeur_conso_interne = 0
        recette_relle = 0
        bank = 0

        for rec in self.env['ostation.shift'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('state', '=', 'valide'), ('etatversementbanque', '=', 'verse')]):
            bank += rec.montanttotal
        for rec in self.env['ostation.shift'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('state', '=', 'valide')]):
            ecart_pompiste += rec.ecarttotal
            recette_relle += rec.montanttotal
        for rec in self.env['ostation.ligneventedetail'].search([('dateshift', '>=', data.get('debut')), ('dateshift', '<=', data.get('fin')), ('state', '=', 'valide')], order = 'dateshift asc, ordreshift asc'):
            if 'su' in rec.idarticle.name.lower() and 'carburant' in rec.idarticle.idcategoriearticle.type:
                volume_su += rec.quantitetheorique 
                prixunitaire_su += rec.prixunitaire
                valeur_su +=  rec.montanttheorique
            if 'ga' in rec.idarticle.name.lower() and 'carburant' in rec.idarticle.idcategoriearticle.type:
                volume_ga += rec.quantitetheorique 
                prixunitaire_ga += rec.prixunitaire
                valeur_ga +=  rec.montanttheorique
            if 'lubrifiant' in rec.idarticle.idcategoriearticle.type:
                valeur_lubrifiant += rec.montanttheorique
            if 'gaz' in rec.idarticle.idcategoriearticle.type:
                valeur_gaz += rec.montanttheorique
            

        for rec in self.env['ostation.ligneversement'].search([('dateshift', '>=', data.get('debut')), ('dateshift', '<=', data.get('fin')), ('state', '=', 'valide')], order = 'dateshift asc, ordreshift asc'):
            if rec.idtypepaiement.id:
                if 'bon' in rec.idtypepaiement.name.lower():
                    valeur_bon += rec.montant
        for rec in self.env['ostation.consommationinterne'].search([('dateshift', '>=', data.get('debut')), ('dateshift', '<=', data.get('fin')), ('state', '=', 'valide')], order = 'dateshift asc, ordreshift asc'):
            valeur_conso_interne += rec.montant
               
        super.append({
            'volume_su': volume_su,
            'prixunitaire_su': prixunitaire_su,
            'valeur_su': valeur_su,
        })
        gasoil.append({
            'volume_ga': volume_ga,
            'prixunitaire_ga': prixunitaire_ga,
            'valeur_ga': valeur_ga,
        })

        # raise UserError(appros)
        return {
            'super': super,
            'gasoil': gasoil,
            'data': data,
            'valeur_lubrifiant': valeur_lubrifiant,
            'valeur_gaz': valeur_gaz,
            'valeur_bon': valeur_bon,
            'valeur_lavage': 0,
            'valeur_boutique': 0,
            'valeur_bon': valeur_bon,
            'ecart_pompiste': ecart_pompiste,
            'valeur_conso_interne': valeur_conso_interne,
            'recette_relle': recette_relle,
            'bank': bank,
        }

class ostation_abstractetatbon(models.AbstractModel):
    _name = 'report.ostation.9bondecarburant'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
        bons = []
    
        for rec in self.env['ostation.recapgrosclient'].search([('dateshift', '>=', data.get('debut')), ('dateshift', '<=', data.get('fin')), ('state', '=', 'valide')]):
            if 'bon' in rec.idtypepaiement.name.lower():
                val = {
                    'date': rec.dateshift,
                    'numero': rec.nbons,
                    'client': rec.idclient.name,
                    'chauffeur': rec.idchauffeur.name,
                    'article': rec.idarticle.name,
                    'quantite': rec.quantite,
                    'prixunitaire': rec.prixunitaire,
                    'montant': rec.montant,
                }
            bons.append(val)
        return {
            'bons': bons,
            'data': data
        }

class ostation_abstractetatmouvementsaccessoiregaz(models.AbstractModel):
    _name = 'report.ostation.5mvtaccessoiregaz'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
        
        resultats = []
        # article=[]
        categoriearticle=[]
        mouvementstock1=[]
        mouvementstock=[]
        appro=[]
        entre = sortie = prix = valeurvente = valeurstockfinal= 0
        ids=[]
        for r in self.env['ostation.article'].search([]):
            if r.idcategoriearticle.type == 'accessoire' :
                ouverture  = sum(m.quantiteentree - m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                entre  = sum(m.quantiteentree  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                sortie = sum(m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                val_mouv = {
                            'id':r.id, 
                            'name':r.name, 
                            'prix':r.prix,
                            'entree': entre,
                            'sortie':sortie,
                            'stockfinal':ouverture+entre-sortie,
                            'ouverture':ouverture,
                            'valeurvente':sortie*r.prix,
                            'valeurstock':(ouverture+entre-sortie)*r.prix
                }
                mouvementstock.append(val_mouv)
        
                
       
        return {
            'data': data,
            'mouvementstock': mouvementstock
        }

class ostation_abstractetatmouvementconsignegaz(models.AbstractModel):
    _name = 'report.ostation.4mvtconsignegaz'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
       
        mouvementstock=[]
        entre = sortie = prix = valeurvente = valeurstockfinal=0

        for r in self.env['ostation.article'].search([]):
            if r.idcategoriearticle.type == 'consignegaz' :
                ouverture  = sum(m.quantiteentree - m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                entre  = sum(m.quantiteentree  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                sortie = sum(m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                #valeurvente = sum(m.montanttheorique  for m in self.env['ostation.ligneventedetail'].search([('dateshift', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                val_mouv = {
                            'id':r.id, 
                            'name':r.name, 
                            'prix':r.prix,
                            'entree': entre,
                            'sortie':sortie,
                            'ouverture':ouverture,
                            'valeurvente':sortie*r.prix,
                            'valeurstockfinal':(ouverture+entre-sortie)*r.prix
                            
                }
                mouvementstock.append(val_mouv)
        
        return {
            'data': data,
            'mouvementstock': mouvementstock
        }

class ostation_abstractetatmouvementlubrifiant(models.AbstractModel):
    _name = 'report.ostation.10mvtlubrifiant'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
       
        mouvementstock=[]
        entre = sortie = prix = valeurvente = valeurstock =0

        for r in self.env['ostation.article'].search([]):
            if r.idcategoriearticle.type == 'lubrifiant' :
                ouverture  = sum(m.quantiteentree - m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                entre  = sum(m.quantiteentree  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                sortie = sum(m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                #valeurvente = sum(m.montanttheorique  for m in self.env['ostation.ligneventedetail'].search([('dateshift', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                val_mouv = {
                            'id':r.id, 
                            'name':r.name, 
                            'prix':r.prix,
                            'entree': entre,
                            'sortie':sortie,
                            'stockfinal':ouverture+entre-sortie,
                            'ouverture':ouverture,
                            'valeurvente':sortie*r.prix,
                            'valeurstock':(ouverture+entre-sortie)*r.prix
                            
                }
                mouvementstock.append(val_mouv)
 
        return {
            'data': data,
            'mouvementstock': mouvementstock
        }

class ostation_abstractetatmouvementsolaire(models.AbstractModel):
    _name = 'report.ostation.11mvtsolaire'
    def _get_report_values(self, docids, data=None):
        domain = [('date', '>=', data.get('debut')), ('date', '<=', data.get('fin'))]
       
        mouvementstock=[]
        entre = sortie = prix = valeurvente = valeurstock = 0

        for r in self.env['ostation.article'].search([]):
            if r.idcategoriearticle.type == 'solaire' :
                ouverture  = sum(m.quantiteentree - m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '<', data.get('debut')), ('idarticle', '=', r.id)]))
                entre  = sum(m.quantiteentree  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                sortie = sum(m.quantitesortie  for m in self.env['ostation.mouvementstock'].search([('date', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                #valeurvente = sum(m.montanttheorique  for m in self.env['ostation.ligneventedetail'].search([('dateshift', '>=', data.get('debut')), ('date', '<=', data.get('fin')), ('idarticle', '=', r.id)]))
                val_mouv = {
                            'id':r.id, 
                            'name':r.name, 
                            'prix':r.prix,
                            'entree': entre,
                            'sortie':sortie,
                            'stockfinal':ouverture+entre-sortie,
                            'ouverture':ouverture,
                            'valeurvente':sortie*r.prix,
                            'valeurstock':(ouverture+entre-sortie)*r.prix
                            
                }
                mouvementstock.append(val_mouv)     
       
        return {
            'data': data,
            'mouvementstock': mouvementstock
        }

class ostation_abstractetatglobal(models.AbstractModel):
    _name = 'report.ostation.12global'
    def _get_report_values(self, docids, data=None):
        
       
        return {
           
        }


