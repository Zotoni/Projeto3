import datetime
import pika
import json
import time

# Connect to a RabbitMQ server running on the local machine
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host="rabbitmq",
     port=5672,
     virtual_host="/"))

channel = connection.channel()

transaction_file = open("transaction2.json")
transactions = json.load(transaction_file)
transaction_file.close()


channel.queue_declare(queue='movimentacao')


# Message attributes
properties = pika.BasicProperties(
    content_type='application/json',
     app_id='producer.py',

)
for transaction in transactions:
    transaction["data"] = str(datetime.datetime.now())

    channel.basic_publish(exchange="amq.fanout",
                      routing_key="",
                      body= json.dumps(transaction), 
                      properties=properties)

    print(f"[x] Sent '{json.dumps(transaction)}'")
  #  time.sleep(1)
channel.close()