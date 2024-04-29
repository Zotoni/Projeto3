import io
import pika
import json
import redis
from minio import Minio
from io import StringIO

lista = []
lista2=[]
#Lista_size =0
transaction_dic={}

#conecta RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(
                                     host = "rabbitmq",
                                     port = 5672,
                                     virtual_host="/",
                                     ))
channel = connection.channel()

print("conectado ao RabbitMQ")

# Connect to Redis
redis_conn = redis.Redis(host='redis', port=6379, db=0)
print("conectado ao Redis")

queue_name="queue_valida_fraude"

channel.queue_declare(queue=queue_name)#cria fila
channel.queue_bind(exchange="amq.fanout", queue=queue_name)#cria binding

def upload_to_minio(stream, filename, tamanho):
    minio_conn = Minio(
    endpoint="minio:9000", 
    access_key="minioadmin", 
    secret_key="minioadmin",
    secure=False)

    bucket_name = "fraude"
    bucket_exists = minio_conn.bucket_exists(bucket_name)
    if bucket_exists:
        print(f"Bucket {bucket_name} já existe!")
    else:
        minio_conn.make_bucket(bucket_name)
        print("Bucket criado com sucesso!")
    
    binaryIO = io.BytesIO(stream.getvalue().encode('utf-8'))
    minio_conn.put_object(
        bucket_name=bucket_name,
        object_name=filename,
        data=binaryIO,
        length=tamanho,
        content_type="text/plain")



    print("Report enviado")

    get_url = minio_conn.get_presigned_url(
    method='GET',
    bucket_name=bucket_name,
    object_name= filename)

    print(f"Download URL: [GET] {get_url}")

def report_fraude(registro):
    print("relatório de fraude")
    file_stream = io.StringIO()
    #write report content to file stream
    file_stream.write("Transação com possível fraude: {}\n".format(json.loads(redis_conn.get(registro))))
    tamanho=file_stream.write("Transação com possível fraude: {}\n".format(json.loads(redis_conn.get(registro))))
    #reset the file stream position to the begining
    file_stream.seek(0)
    #file_stream.close() isso estava dando erro pq estava manipulando a stream em outra função e ela fechava aqui
    conta =registro
    upload_to_minio(file_stream, conta, tamanho)

def registra_fraude(registro):
    global lista, lista2
    print("fraude detectada na transação nº: ", registro)
    lista.remove(registro)
    report_fraude(registro)

def detecta_fraude(p1):#parametros chave_trans 
    global lista,  lista2, transaction_dic
    lista.append(p1) # serve para guardar as chaves de comparação (exclui chave de comparação quando encontra fraude)
    lista2.append(p1) # serve para controlar o loop (guardas todas as chaves)
    p2 = len(lista2)
    compara_dic={}
    for i in range(p2):
        compara_dic =json.loads(redis_conn.get(lista2[i]))
        if (transaction_dic.get('account_number') == compara_dic.get('account_number')) and (transaction_dic.get('local') != compara_dic.get('local')):
            registra_fraude(transaction_dic.get('chave_trans'))

def chamado_transacao_consumida(channel, method_frame, header_frame, body):
    global transaction_dic 
    transaction_dic = json.loads(body.decode('utf-8'))
    print("Transação: ", transaction_dic['chave_trans'])
    redis_conn.set(transaction_dic['chave_trans'], json.dumps(transaction_dic))
    detecta_fraude(transaction_dic['chave_trans'])

channel.basic_consume(queue=queue_name, 
                      on_message_callback=chamado_transacao_consumida, auto_ack=True)

print("Esperando por mensages. Para sair pressione CTRL+C")
channel.start_consuming()
