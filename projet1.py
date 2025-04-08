import mysql.connector
from plyer import notification
import requests
import  random
from datetime import datetime, timedelta
try:
    #connexion à mysql
    connexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="reporting_ventes")
    curseur=connexion.cursor()
    #créer les tables
    curseur.execute(""" create table if not exists produits(
                    id int primary key,
                    nom varchar(255),
                    description text,
                    prix decimal(10,2),
                    stock int)""")
    print("✅ table produits créée")
    curseur.execute(""" create table if not exists ventes(
                     id int primary key,
                     produit_id int,
                     quantite int,
                     montant decimal(10,2),
                     date date,
                     foreign key (produit_id) references produits(id))""")
    print("✅ table ventes créée")
    curseur.execute(""" CREATE TABLE IF NOT EXISTS inventaire (
            produit_id INT PRIMARY KEY,
            stock_initial INT,
            stock_actuel INT,
            besoin_reapprovisionnement BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (produit_id) REFERENCES produits(id))""")

    print("✅ table inventaire créée")
except mysql.connector.Error as err:
    print("❌ Erreur de connexion à MySQL :", err)
def envoyer_notification(titre, message):
    notification.notify(
        title=titre,
        message=message,
        timeout=5 )

try:
    #récupération des données depuis Fake Store API
    response = requests.get("https://fakestoreapi.com/products")
    produits = response.json()
    print("✅ Données des produits récupérées.")
    #insertion des données dans la table produits
    for p in produits:
        curseur.execute(""" insert into produits(id, nom, description, prix)
                        value(%s, %s, %s, %s)
                        on duplicate key update
                        nom = values(nom),
                        description = values(description),
                        prix = values(prix)""",
                        (p['id'], p['title'], p['description'], p['price']))
    print("✅ Données des produits insérées dans la table.")
    connexion.commit()
except requests.exceptions.RequestException as e:
    print(f"❌ Erreur lors de la récupération des données de l'API : {e}")
except mysql.connector.Error as err:
    print(f"❌ Erreur lors de l'insertion des données dans MySQL : {err}")

try:
    curseur.execute("delete from ventes")
    #insértion des données simulées dans la table ventes
    vente_id = 1
    for p in range(1, 20): # Pour les 20 produits
        for i in range(random.randint(1,5)):
            # On récupère le prix du produit depuis la table produits
            curseur.execute("SELECT prix FROM produits WHERE id = %s", (p,))
            prix = curseur.fetchone()[0]  # On extrait le prix
            quantite_vendue = random.randint(1, 10)  # On génère une quantité aléatoire
            montant = round(quantite_vendue * prix, 2)  # On calcule le montant total

            date = datetime.now() - timedelta(days=random.randint(0, 30))  # Date de vente aléatoire

            # Insertion dans la table ventes
            curseur.execute("""
            INSERT INTO ventes (id, produit_id, quantite, montant, date)
            VALUES (%s, %s, %s, %s, %s)""", (
            vente_id,
            p,
            quantite_vendue,
            montant,
            date.strftime('%Y-%m-%d')))
            vente_id += 1


    #insértion des données dans la table inventaire
    curseur.execute("delete from inventaire")
    for produit_id in range(1, 6):  # Encore 5 produits
       stock_initial = random.randint(50, 170)  # Stock initial aléatoire entre 50 et 200
       stock_actuel = stock_initial - random.randint(0, 30)  # Stock actuel après ventes

       curseur.execute(""" INSERT INTO inventaire (produit_id, stock_initial, stock_actuel)
           VALUES (%s, %s, %s)""",
            (produit_id,
            stock_initial,
            stock_actuel ))

    #enregistrer les changements dans la base
    connexion.commit()
    print("✅ Données insérées avec succès dans les tables 'ventes' et 'inventaire'.")
except mysql.connector.Error as err:
    print("❌ Erreur lors de l'insertion des données dans MySQL :", err)

try:
    # Mise à jour du stock dans la table inventaire après chaque vente
    for produit_id in range(1, 6):  # pour chaque produit
        # Récupérer le stock actuel dans la table inventaire
        curseur.execute("SELECT stock_actuel FROM inventaire WHERE produit_id = %s", (produit_id,))
        stock_actuel = curseur.fetchone()[0]

        # Récupérer les ventes du produit
        curseur.execute("""
            SELECT SUM(quantite) FROM ventes WHERE produit_id = %s AND date >= CURDATE() - INTERVAL 1 MONTH
        """, (produit_id,))
        quantite_vendue = curseur.fetchone()[0] or 0  # Si aucune vente, retour 0

        # Calcul du nouveau stock
        nouveau_stock = stock_actuel - quantite_vendue

        # Mise à jour de l'inventaire
        curseur.execute("""
            UPDATE inventaire 
            SET stock_actuel = %s, besoin_reapprovisionnement = %s 
            WHERE produit_id = %s""", (nouveau_stock, nouveau_stock < 50, produit_id))
        if nouveau_stock < 50 :
            message = f"le produit {produit_id} nécessite un réapprovionnement. Stock actuel: {nouveau_stock}."
            envoyer_notification("Alerte Réapprovisionnement", message)
            print(f"Notification envoyée pour le produit {produit_id}:{nouveau_stock}")
    connexion.commit()
    print("✅ Inventaire mis à jour avec succès.")
except mysql.connector.Error as err:
    print(f"❌ Erreur lors de la mise à jour de l'inventaire : {err}")
try:
        # Rapport des ventes du mois en cours
        curseur.execute("""
            SELECT produits.nom, SUM(ventes.quantite) AS total_vendu, SUM(ventes.montant) AS revenu_total
            FROM ventes
            JOIN produits ON ventes.produit_id = produits.id
            WHERE ventes.date >= CURDATE() - INTERVAL 1 MONTH
            GROUP BY produits.nom
            ORDER BY revenu_total DESC
        """)

        ventes = curseur.fetchall()
        print("📊 Rapport des ventes du mois :")
        for vente in ventes:
            print(f"Produit: {vente[0]}, Quantité vendue: {vente[1]}, Revenu total: {vente[2]:.2f} €")

except mysql.connector.Error as err:
        print(f"❌ Erreur lors du reporting des ventes : {err}")


input("Appuie sur Entrée pour quitter...")














