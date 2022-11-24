# tppo_1422

## Сервер:

Запуск:
```shell
python3 tppo_server_1422.py 
```
Опционально можно передать адрес сервера и порт, например

```shell
python3 tppo_server_1422.py 127.0.0.1 9999
```

## Клиент:

Запуск:
```shell
python3 tppo_client_1422.py 
```
Опционально можно передать адрес сервера и порт, например

```shell
python3 tppo_client_1422.py 127.0.0.1 9999
```

### Команды

#### `get`
`get` позволяет получить информацию о состоянии устройства/отдельных его атрибутов. Синтаксис:
```shell
get <device> <attribute1> <attribute2> 
```
`<attribute>` необязателен.

Примеры:
```shell
get relay
get relay ch1
```

#### `set`
`set` позволяет задать состояние устройства, конкретных его компонентов:
```shell
set <device> <attribute1> <attribute1_value> <attribute2> <attribute2_value>
```

Примеры:
```shell
set relay ch1 ON
set relay ch2 OFF ch5 ON
```

#### `subscribe` 
`subscribe` позволяет подписаться на уведомления об изменении одного или нескольких атрибутов устройства.
```shell
subscirbe <device> <attribute1> <attribute2>
```

Примеры:
```shell
subscirbe relay ch1 ch3
```

#### `unsubscribe` 
`unsubscribe` позволяет отписаться от получения уведомлений об изменении атрибутов устройства.

Примеры:
```shell
unsubscirbe
```

## Устройство
Устройство определяется `XML` файлом, в качестве корневого тега используется название устройства, далее для каждого
атрибута указывается текущее состояние и возможные состояния через запятую и пробел.

Пример
```xml
<relay>
	<ch1>
		<state>ON</state>
		<possible_states>ON, OFF</possible_states>
	</ch1>
....
```

Список устройств оформляется в файле `server/constants.py`

## Ошибки
Все ошибки, при наличии, возвращаются клиенту и отображаются при помощи соответствующего сообщения.