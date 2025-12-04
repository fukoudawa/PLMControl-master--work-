from typing import Callable, Optional
from numpy import isin
from paho.mqtt import client as mqtt_client

class MQTTDevice:
    def __init__(self, configs: dict | None = None) -> None:
        self.__broker   : str | None = None                  # адресс брокера
        self.__port     : int | None = None                  # порт брокера
        self.__id       : str | None = None                  # ID клиента
        self.__client   : mqtt_client.Client | None = None   # экземпялр клиента
        self.root_topic : str  = ""                          # корневая тема, публикуемая клиентом
        self.__isInited : bool = False                       # флаг инициализации  
           
        if isinstance(configs, dict): self.configure(configs)

    @property
    def isOnline(self) -> bool: 
        return self.__client.is_connected() if self.__isInited else False

    @property
    def id(self) -> str: 
        return self.__id

    @property
    def broker(self) -> str: 
        return self.__broker

    @property
    def port(self) -> int: 
        return self.__port

    def configure(self, configs: dict) -> bool:
        """ 
        Сконфигурировать MQTT клиент
            
        Parameters:
            configs (dict): параметры конфигурации
            
        Returns:
            bool: True, если клиент успешно сконфигурирован
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

        Returns:
            bool: True, если клиент успешно подключен к брокеру
        """
        
        if not self.__isInited:
            print("[!] Failed to connect to the MQTT Broker: device is not configurated")
        else:
            # Если переданы новые значения для брокера и порта, обновляем их
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

        Returns:
            bool: True, если клмент успешно отключен
        """
        
        if self.__isInited:
            self.__client.loop_stop()
            self.__client.disconnect()      

        return not self.isOnline
            
    ''' ---------------------------------------- @Decorators ---------------------------------------- '''
    
    def topic(title: str) -> Callable:
        """ 
        Декоратор, публикующий значение, возвращаемое функцией, в топик, 
        название которого имеет вид '{root_topic}/{title}'

        Parameters:
            title (str): название топика

        Returns:
            Callable: декоратор, публикующий значение, возвращаемое функцией, в топик
        """
        
        def wrapper(func: Callable[[], float]) -> Callable[..., float]:
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

    ''' -------------------------------------- Dunder Methods -------------------------------------- '''

    def __del__(self) -> None:
        self.disconnect()  

    def __repr__(self) -> str:
        return f"MQTTDevice(id={self.__id}, broker={self.__broker}, port={self.__port})"

    def __eq__(self, obj: object) -> bool:
        return self.__id == obj.id if isinstance(obj, MQTTDevice) else False
    

class MQTTProducer:
    def __init__(self, configs: Optional[dict] = None) -> None:
        self.__broker   : str | None = None                  # адресс брокера
        self.__port     : int | None = None                  # порт брокера
        self.__id       : str | None = None                  # ID клиента
        self.__client   : mqtt_client.Client | None = None   # экземпялр клиента
        self.__isInited : bool = False                       # флаг инициализации  

        if isinstance(configs, dict): self.configure(configs)

    @property
    def isOnline(self) -> bool: 
        return self.__client.is_connected() if isinstance(self.__client, mqtt_client.Client) else False

    @property
    def id(self) -> str: 
        return self.__id

    @property
    def broker(self) -> str: 
        return self.__broker

    @property
    def port(self) -> int: 
        return self.__port

    def configure(self, configs: dict) -> bool:
        """
        Настротить объект MQTTProducer

        Parameters:
            configs (dict): параметры подключения

        Returns:
            bool: True, если конфигурация прошла успешно
        """

        try:
            self.__broker = configs["broker"]
            self.__port   = configs["port"]
            self.__id     = configs["id"]
            self.__client = mqtt_client.Client(
                client_id            = self.__id, 
                callback_api_version = mqtt_client.CallbackAPIVersion.VERSION2
            )
            self.__isInited = True
        except KeyError as error:
            self.__client   = None
            self.__isInited = False
            print(f"[!] Failed to configure the device's basic operating parameters: missing {error}")

        return self.__isInited

    def connect(self) -> bool:
        """ 
        Подключиться к MQTT брокеру (без аутентификации)

        Returns:
            bool: True, если клиент успешно подключен к брокеру
        """

        if self.__isInited:
            if self.isOnline: self.disconnect()
            try:
                self.__client.connect(self.__broker, self.__port)
                self.__client.loop_start()
            except Exception as e:
                print(f"[!] Failed to connect to the MQTT Broker: {e}")
        else:
            print("[!] Failed to connect to the MQTT Broker: device is not configurated")

        return self.isOnline
    
    def disconnect(self) -> bool:
        """
        Отключиться от MQTT брокера

        Returns:
            bool: True, если успешно отключено (или уже отключено)
        """

        if self.isOnline:
            self.__client.loop_stop()  # Останавливаем внутренний цикл выборки сообщений
            self.__client.disconnect() # Отключаемся от брокера

        return not self.isOnline    

    def publish(self, data: float, topic: str) -> bool:
        """
        Опубликовать данные в указанный топик

        Parameters:
            data (float): Данные для публикации
            topic (str): Топик в который публикуется сообщение

        Returns:
            bool: True если публикация прошла успешно
        """

        if self.isOnline:
            try:
                # Формируем полный топик и публикуем данные
                self.__client.publish(f"{self.__id}/{topic}", f"{data}")
                return True
            except Exception as e:
                print(f"[!] Failed to publish the message with topic '{self.__id}/{topic}': {e}")
                return False
        else:
            return False

    ''' -------------------------------------- Dunder Methods -------------------------------------- '''

    def __del__(self) -> None:
        self.disconnect()  

    def __repr__(self) -> str:
        return f"MQTTProducer(id={self.__id}, broker={self.__broker}, port={self.__port})"

    def __eq__(self, obj: object) -> bool:
        return self.__id == obj.id if isinstance(obj, MQTTProducer) else False