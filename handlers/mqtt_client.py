from typing import Callable, Optional
from paho.mqtt import client as mqtt_client

class MQTTDevice:
    def __init__(self, configs: dict | None = None) -> None:
        self.__broker   : str | None = None                # адресс брокера
        self.__port     : int | None = None                # порт брокера
        self.__id       : str | None = None                # ID клиента
        self.__client   : mqtt_client.Client | None = None # экземпялр клиента
        self.root_topic : str  = ""                        # корневая тема, публикуемая клиентом
        self.__isInited : bool = False                     # флаг инициализации  
           
        if isinstance(configs, dict): self.configure(configs)
        
    def __del__(self) -> None:
        self.disconnect()   
    
    @property
    def isOnline(self) -> bool: 
        return self.__client.is_connected() if self.__isInited else False
    
    def configure(self, configs: dict) -> bool:
        """ 
            Сконфигурировать MQTT клиент
            Parameters:
                configs (dict): параметры конфигурации
        """

        # Конфигурирование критических параметров (необходимых для работы клиента)
        try:
            self.__broker = configs["broker"]
            self.__port   = configs["port"]
            self.__id     = configs["id"]
            self.__client = mqtt_client.Client(
                client_id            = self.__id, 
                callback_api_version = mqtt_client.CallbackAPIVersion.VERSION2
            )
        except KeyError as error:
            self.__client = None
            print(f"[!] Failed to configure the device's basic operating parameters: missing {error}")
            
        self.__isInited = True if isinstance(self.__client, mqtt_client.Client) else False
        
        # Конфигурирование оставшихся параметров
        if self.__isInited:
            self.root_topic = configs["root_topic"] if "root_topic" in configs else self.__id
            
        return self.__isInited
    
    def connect(self, broker: str | None = None, port: int | None = None) -> bool:
        """ 
            Подключиться к MQTT брокеру (без аутентификации)
            Parameters:
                broker (str): адресс брокера
                port (int): порт брокера
        """
        
        if not self.__isInited:
            print("[!] Failed to connect to the MQTT Broker: device is not configurated")
        else:
            if isinstance(broker, str) : self.__broker = broker
            if isinstance(port, int)   : self.__port   = port
            try:
                # Подключение и поддержка связи в отдельном потоке
                self.__client.connect(self.__broker, self.__port)
                self.__client.loop_start()
            except Exception as e:
                print(f"[!] Failed to connect to the MQTT Broker ({self.__broker}, {self.__port}): {e}")

        return self.isOnline
    
    def disconnect(self) -> bool:
        """ 
            Отключиться от MQTT брокера 
        """
        
        if self.__isInited:
            self.__client.loop_stop()
            self.__client.disconnect()      
        return not self.isOnline
            
    ''' ---------------------------- @Decorators ---------------------------- '''
    
    def topic(title: str) -> Callable:
        """ 
            Декоратор, публикующий значение, возвращаемое функцией,
            в топик, название которого имеет вид '{root_topic}/{title}'
        """
        
        def wrapper(func: Callable) -> Callable:
            def publish(self, *args, **kwargs) -> float: 
                measure = func(self)
                
                if self.isOnline:
                    try:
                        self.__client.publish(f"{self.root_topic}/{title}", f"{measure}")
                    except Exception as e:
                        print(f"[!] Failed to publish the message of '{self.__id}' with topic '{self.root_topic}/{title}': {e}")
                        
                return measure
            return publish
        return wrapper 
    

class MQTTProducer:
    def __init__(self, configs: Optional[dict] = None) -> None:
        self.__client : mqtt_client.Client | None = None
        self.__id     : str                | None = None

        if isinstance(configs, dict): self.connect(configs)

    def __del__(self) -> None:
        self.disconnect()

    @property
    def isOnline(self) -> bool: 
        return self.__client.is_connected() if isinstance(self.__client, mqtt_client.Client) else False

    def connect(self, configs: dict) -> bool:
        """ Подключиться к MQTT брокеру (без аутентификации) с
            параметрами брокера и producer'а configs
        """

        if self.isOnline: self.disconnect()

        try:
            self.__id = configs["id"]
            self.__client = mqtt_client.Client(
                client_id            = self.__id, 
                callback_api_version = mqtt_client.CallbackAPIVersion.VERSION2
            )
            self.__client.connect(configs["broker"], configs["port"])
            self.__client.loop_start()
        except Exception as e:
            print(f"[!] Failed to connect to the MQTT Broker: {e}")

        return self.isOnline
    
    def disconnect(self) -> bool:
        """ Отключиться от MQTT брокера """

        if self.isOnline:
            self.__client.loop_stop()
            self.__client.disconnect()      
        return not self.isOnline

    def publish(self, data: float, topic: str) -> bool:
        """ Опубликовать data в topic """

        if self.isOnline:
            try:
                self.__client.publish(f"{self.__id}/{topic}", f"{data}")
                return True
            except Exception as e:
                print(f"[!] Failed to publish the message with topic '{self.__id}/{topic}': {e}")
                return False
        else:
            return False
