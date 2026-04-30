# Correction 02 — Kafka

**À lire après avoir fait l'exercice.**

---

## Réponses aux questions

**1. Qu'est-ce qu'un topic Kafka ?**

Un topic est un canal de communication nommé dans lequel les producers publient
et depuis lequel les consumers lisent. C'est comparable à un fichier de logs
en écriture continue : les messages s'accumulent dans l'ordre d'arrivée.

Contrairement à une queue classique (RabbitMQ, SQS), les messages dans Kafka
ne sont pas supprimés après lecture. Ils persistent pendant une durée configurable
(par défaut 7 jours). N'importe quel consumer peut les relire.

Dans le projet : `crypto-trades` est le topic. Le producer Binance y publie,
le consumer TimescaleDB y lit.

**2. Pourquoi le consumer peut-il relire des messages anciens avec "earliest" ?**

Kafka associe un numéro séquentiel à chaque message : l'offset.
Le consumer garde en mémoire (dans Kafka, via le `group_id`) le dernier offset
qu'il a lu.

- `auto_offset_reset="earliest"` : si le groupe n'a jamais lu ce topic, commence
  depuis le début (offset 0). C'est pour les tests et le développement.
- `auto_offset_reset="latest"` : commence seulement à partir des nouveaux messages.
  C'est le comportement production — on ne veut pas retraiter l'historique au démarrage.

**3. Qu'est-ce qu'un group_id ?**

Le `group_id` identifie un groupe de consumers qui se partagent la lecture d'un topic.
Kafka mémorise l'offset de chaque groupe séparément.

Si tu relances ton consumer avec le même `group_id`, il reprend là où il s'est arrêté.
Si tu changes le `group_id`, Kafka croit que c'est un nouveau consumer — il repart
depuis `auto_offset_reset`.

Dans le projet : un seul consumer avec `group_id="crypto-consumer-group"`.
Si le consumer plante et redémarre, il reprend exactement là où il était.

**4. Pourquoi encode-t-on le message en utf-8 ?**

Kafka transporte des bytes, pas des strings Python. `json.dumps()` produit une
string Python. `.encode("utf-8")` la convertit en bytes.

À la lecture, le processus inverse : `msg.value` est en bytes, `.decode("utf-8")`
le reconvertit en string, `json.loads()` le parse en dict.

**5. Différence entre send() et send_and_wait() ?**

`send()` envoie le message de façon asynchrone sans attendre la confirmation.
Plus rapide, mais tu ne sais pas si le message a bien été reçu par Kafka.

`send_and_wait()` attend la confirmation que Kafka a bien reçu et stocké le message.
Légèrement plus lent, mais garanti. Pour un pipeline de trading, on préfère
la garantie à la vitesse.

---

## Réponse à l'étape 6 — Persistance

Quand tu relances le consumer après avoir envoyé de nouveaux messages :
- Si `group_id` identique + `earliest` → tu vois TOUS les messages depuis le début.
- Si `group_id` identique + offset mémorisé → tu vois seulement les nouveaux.

C'est la force de Kafka : les messages ne disparaissent pas à la lecture.

---

## Erreurs fréquentes à cet exercice

**"NoBrokersAvailable"**
Kafka n'est pas encore prêt. Attends 10-15 secondes après `docker compose up` et réessaie.

**"TopicAuthorizationFailedException"**
Le topic n'existe pas encore. Refais l'étape 2 de création du topic.

**Le consumer ne reçoit rien**
Vérifie que `auto_offset_reset="earliest"` est bien mis et que le `group_id`
est différent de celui utilisé lors d'une exécution précédente (ou supprime
les offsets en recréant le container Kafka).
