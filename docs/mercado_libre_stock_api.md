Stock Multi Origen
Importante:
Para poder realizar pruebas debes solicitar la ambientación de tus usuarios de pruebas con este formulario. Dichas activaciones serán realizadas los días viernes (cada 15 días).
En Brasil (MLB), no es posible crear depósitos en diferentes estados. El seller solo puede crear depósitos en el mismo estado de su CNPJ.
El objetivo de Stock Multi Origen es representar a un vendedor que tiene múltiples ubicaciones o tiendas.

El propósito final, junto con la iniciativa de Precios por Variación, es permitir que los productos de un mismo vendedor tengan stock distribuido en sus diversas ubicaciones.

Se introduce el concepto de seller_warehouse para representar a un vendedor que cuenta con más de una tienda o punto de venta.

Cada vendedor mantendrá una única logística, lo que significa que, aunque un vendedor tenga varias ubicaciones, todas operarán bajo la misma logística configurada en su cuenta, como, por ejemplo, Mercado Envíos Colecta (crossdocking).

El modelo de Multi Origen no es compatible con publicaciones ME1. Los sellers pueden operar simultáneamente con los modelos logísticos ME1 y ME2, manteniendo ítems distintos en cada uno. Para los artículos publicados en ME1, incluso si el seller realiza una distribución de stock entre depósitos, esa información solo se considerará a efectos de registro por depósito. En el momento de la venta, el descuento de la unidad vendida se aplicará en el depósito con la mayor cantidad disponible, pero esto no implica que el envío se realizará desde ese depósito.

En esta documentación, encontrarás información importante para cada uno de los flujos que se verán impactados por esta iniciativa, comenzando por:

Gestión de vendedores.
Publicación de ítem con stock multi origen
Gestión de stock por depósito
Identificar vendedor Multi-Warehouse
Nota:

No todos los vendedores tendrán la funcionalidad activada en su cuenta. La activación de los vendedores será controlada y estará sujeta a criterios definidos por Mercado Libre, como el tipo de logística que operan, las direcciones desde las que despachan, entre otros.


Para identificar que el usuario tiene la funcionalidad activada en su cuenta, utilizaremos el tag "warehouse_management" en /users.

Llamada:

curl -X GET https://api.mercadolibre.com/users/$USER_ID -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo:

curl -X GET https://api.mercadolibre.com/users/1008002397 -H 'Authorization: Bearer $ACCESS_TOKEN'
Respuesta:

{
  "id": 1008002397,
  "nickname": "TETE9326760",
  "registration_date": "2021-10-27T14:48:55.000-04:00",
  "first_name": "Test",
  "last_name": "Test",
  "gender": "",
  "country_id": "MX",
  ...
  "tags": [
    "normal",
    "user_product_seller",
    "warehouse_management",
    "mshops"
  ],
  ...
}
Gestión de depósitos
Nota:

La posibilidad de crear ubicaciones para un mismo seller_id únicamente está disponible desde la cuenta de cada vendedor por medio del panel de Mercado Libre, en Ventas -> Preferencias de venta -> Mis depósitos.


Búsqueda de depósitos (stores) de un usuario
Para identificar los depósitos creados por cada usuario, debes utilizar el siguiente endpoint:

Llamada:

curl -X GET https://api.mercadolibre.com/users/$USER_ID/stores/search?tags=stock_location -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo:

curl -X GET https://api.mercadolibre.com/users/1008002397/stores/search?tags=stock_location -H 'Authorization: Bearer $ACCESS_TOKEN'
Respuesta:


{
    "paging": {
        "limit": 50,
        "total": 2
    },
    "results": [
        {
            "id": "100",
            "user_id": "200",
            "description": "my store",
            "status": "active",
            "location": {
                "address_id": 501,
                "address_line": "Calle 31 Pte 260",
                "street_name": "Calle 31 Pte",
                "street_number": 260,
                "latitude": 21.1637963,
                "longitude": -86.8737132,
                "city": "Cancún/Benito Juárez",
                "state": "Quintana Roo",
                "country": "Mexico",
                "zip_code": "77518"
            },
            "tags": [
                "stock_location"
            ],
            "network_node_id": "123451",
            "services": {
                "stock_location": [
                    "cross_docking",
                    "xd_drop_off"
                ]
            }
        },
        {
            "id": "101",
            "user_id": "200",
            "description": "my store 2",
            "status": "active",
            "location": {
                "address_id": 502,
                "address_line": "Calle 30 Pte 300",
                "street_name": "Calle 30 Pte",
                "street_number": 300,
                "latitude": 21.1637963,
                "longitude": -86.8737132,
                "city": "Cancún/Benito Juárez",
                "state": "Quintana Roo",
                "country": "Mexico",
                "zip_code": "77518"
            },
            "tags": [
                "stock_location"
            ],
            "network_node_id": "571615",
            "services": {
                "stock_location": [
                    "drop_off",
                    "self_service"
                ]
            }
        }
    ]
}
Creación de ítems Multi-Warehouse
La nueva estructura del Item, con su User Product y los Stocks Locations estará en el siguiente formato:


En donde el User Product agrupará todos los items que coincidan, basado en las reglas de UP, pero ahora también tendrá la entidad Stock_Location para agrupar el stock de los items, pudiendo identificar la cantidad disponible en cada depósito (store).


Para la creación de nuevos ítems con stock asignado a los depósitos, tanto tradicionales como de catálogo en los vendedores con el tag "warehouse_management", debes utilizar el siguiente recurso:

Nota:

Utiliza la documentación de publicar un producto para conocer la estructura completa de publicar un Item.

Llamada:

curl POST --'https://api.mercadolibre.com/items/multiwarehouse' -H 'Content-Type: application/json' -H 'Authorization: Bearer $ACCESS_TOKEN' -d 
    {
        "title": "Item Lata de tomate ",
        "category_id": "MLB455668",
        "price": 1000,
        "listing_type_id": "gold_special",
        "currency_id": "ARS",
        ...
        "channels": [
            "marketplace"
        ],
        "stock_locations": [
       {
        "store_id": "123456",
          "network_node_id": "123451",
          "quantity": 10
       }
       ...
    ] 
    }
Respuesta:

{
    "id": "MLM2198240631",
    "site_id": "MLM",
    "title": "Item Lata De Tomate",
    "seller_id": 123456789,
    "category_id": "MLM191212",
    "user_product_id": "MLMU123456789",
    "price": 1000,
    "base_price": 1000,
    ...
    "channels": [
        "marketplace"
    ],
    "stock_locations": [
        {
            "store_id": "123456",
            "quantity": 10,
            "network_node_id": "MXP123451"
        }
    ]
 } 
    
Códigos de Estado de respuesta:

Código	Mensaje	Descripción	Recomendación
201	OK	Item creado	-
400	the fields [stock_locations] are required for requested call	Campo stock_locations no encontrado en la requisición	Incluir al menos una de las tiendas del vendedor para crear el ítem
400	store does not belong to seller: 000	El id de la tienda no pertenece al dicho usuario	Revisar las tiendas del vendedor
400	store not found: 000	El id de la tienda no existe	Revisar las tiendas del vendedor
400	the fields [available_quantity] are invalid for requested call	El campo available_quantity no es permitido para este usuario	Una vez que el usuario tiene la etiqueta warehouse_management, ya no se puede publicar con available_quantity, debe incluir stock_locations
Consideraciones:

Tanto el store_id como el network_node_id, van a estar en el response de la búsqueda por las tiendas del vendedor.
Luego de la publicación, no será más posible encontrar stock_location en la petición de Item, sino que debe empezar a utilizar el recurso de consulta de stock de user_product.
Debes guardar el user_product_id de la respuesta que será utilizado más adelante para la gestión de stock.

Consultar detalle de stock depósitos (User Products)
Para consultar el stock de los depósitos el siguiente endpoint indicando el user_product_id del Ítem creado.

Llamada:

curl -X GET https://api.mercadolibre.com/user-products/$USER_PRODUCT_ID/stock -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo:

curl -X GET https://api.mercadolibre.com/user-products/MLMU123456789/stock -H 'Authorization: Bearer $ACCESS_TOKEN'
Respuesta:

{
    "locations": [
        {
            "type": "seller_warehouse",
            "network_node_id": "123451",
            "store_id": "9876543",
            "quantity": 15
        },
        {
            "type": "seller_warehouse",
            "network_node_id": "571615",
            "store_id": "9876553",
            "quantity": 25
        }
    ],
    "user_id": 1234,
    "id": "MLMU123456789"
 }
 
 
Gestión de stock por ubicación
Nota:

En el paso anterior, al consultar el stock, se retornará el header "x-version", el cual tendrá un valor entero (tipo long) que representará la versión actual de stock. Este header debe ser enviado al realizar un PUT en /stock/. Si no se envía, retornará un error 400 bad request.


Para modificar el stock de cada depósito, deberás tener previamente el user_product_id, el store_id y el network_node_id.

El siguiente PUT cambiará el stock actual de cada depósito (store). En caso que el store tenga stock 0, se asignará la cantidad del PUT.

Llamada:

>curl -X PUT https://api.mercadolibre.com/user-products/$USER_PRODUCT_ID/stock/type/seller_warehouse -H 'x-version: $HEADER' -H 'Content-Type: application/json' -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo:

curl -X PUT https://api.mercadolibre.com/user-products/MLMU123456789/stock/type/seller_warehouse -H 'x-version: 1' -H 'Content-Type: application/json' -H 'Authorization: Bearer $ACCESS_TOKEN' -d '
    {
    "locations": [
       {
        "store_id": "123456",
        "network_node_id": "MXP123451", //el campo network_node_id es opcional y no se valida en la petición
          "quantity": 10
       },
       { 
        "store_id": "123457",
          "network_node_id": "MXP571615",
          "quantity": 5
       },
       { 
        "store_id": "123458",
          "network_node_id": "MXP725258",
          "quantity": 20
       }
    ]
    }
Respuesta:

{
    "user_id": 123456789,
    "product_release_date": null,
    "id": "MLMU123456789",
    "locations": [
        {
            "store_id": "123456",
            "network_node_id": "MXP123451",
            "type": "seller_warehouse",
            "quantity": 10
        },
        {
            "store_id": "123457",
            "network_node_id": "MXP571615",
            "type": "seller_warehouse",
            "quantity": 5
        },
        {
            "store_id": "123458",
            "network_node_id": "MXP725258",
            "type": "seller_warehouse",
            "quantity": 20
        }
    ]
 }
 
Códigos de Estado de respuesta:

Código	Mensaje	Descripción	Recomendación
200	OK	Actualización exitosa	-
400	Missing X-Version header	Header “x-version” no informado	Debes informar el Header “x-version”
409	Version mismatch	El header “x-version” informado es incorrecto	Haz un GET en /user-product para obtener el header “x-version” actualizado
400	store does not belong to seller: 000	El id de la store no pertenece al dicho usuario	Revisar las stores del vendedor
400	store not found: 000	El id de la store no existe	Revisar las stores del vendedor
400	store is not configured to be a stock location	El store no está configurado para multiorigen	Indique que el vendedor revise el dicho store por el panel de Mercado Libre
400	store cannot be null or empty	Campo store no informado	Incluir al menos una de las stores del vendedor para actualizar stock del UP
Nota:
Para la pos-venta, consulte la documentación de Orders y/o de Envíos para conocer pedidos con stores por el campo "node_id".
Nota:

Para la pos-venta, consulte la documentación de Orders y/o de Envíos para conocer pedidos con stores por el campo "node_id".


Stock distribuido
Stock Distribuido tiene como objetivo permitir que los vendedores configuren diferentes ubicaciones del stock (stock_locations) a un mismo User Product.



Tipos de stock
Para la gestión del stock definimos las tres siguientes tipologías de stock_locations:

Location type	Caso de uso	Gestor del stock	Permite editar stock vía API
meli_facility	El vendedor envía su stock a los depósitos de Fulfillment de Mercado Libre.	Mercado Libre (Full)	No.
selling_address	Depósito de origen del vendedor que representa las logísticas que no son fullfillment tales como: crossdocking, xd_drop_off y flex.	Usuario (Vendedor)	Sí, en los sites donde está encendida la experiencia stock distribuido full y flex, es decir en MLA y MLC.
seller_warehouse	Múltiples orígenes de stock gestionados por el vendedor. Permite al vendedor gestionar el stock de varios depósitos que corresponden a las ubicaciones donde tiene su inventario.	Usuario (Vendedor)	Sí, siempre que el seller esté configurado en la experiencia de multi origen y cuente con la tag de multi_warehouse_management.

Diagrama de ejemplo de stock distribuido para un User Product con Convivencia Full - Flex en sites donde el seller puede gestionar el stock de flex:


Nota:

Como lo evidencia el gráfico el stock será compartido entre channels (marketplace y MShops). Esto hasta 31 de diciembre de 2025 cuando Mshops deje de estar disponible.

Diagrama de ejemplo de stock distribuido para un seller activo a multiorigen y un User Product con stock en diferentes locations:



Obtener detalle de stock
Tenga en cuenta que un mismo UP podrá tener hasta dos tipologías, ya sea (selling_address y meli_facility) o (seller_warehouse y meli_facility).

Para consultar el stock asociado a un User Product deberás hacer la siguiente requisición.

Llamada:

curl -X GET https://api.mercadolibre.com/user-products/$USER_PRODUCT_ID/stock -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo:

curl -X GET https://api.mercadolibre.com/user-products/MLAU123456789/stock -H 'Authorization: Bearer $ACCESS_TOKEN'
Ejemplo de respuesta para tipología selling_address:

{
  "locations": [
    {
      "type": "selling_address",
      "quantity": 5
    }
  ],
  "user_id": 1234,
  "id": "MLBU206642488"
}
Ejemplo de respuesta para tipología meli_facility:

{
  "locations": [
    {
      "type": "meli_facility", //fulfillment
      "quantity": 5
    }
  ],
  "user_id": 1234,
  "id": "MLBU206642488"
}
Ejemplo de respuesta para tipología seller_warehouse:

{
   "locations": [
       {
           "type": "seller_warehouse",
           "network_node_id": "MXP123451",
           "store_id": "9876543",
           "quantity": 15
       },
       {
           "type": "seller_warehouse",
           "network_node_id": "MXP123452",
           "store_id": "9876553",
           "quantity": 15
       }
   ],
   "user_id": 1234,
   "id": "MLAU123456789"
}
Consideraciones:

Al consultar el detalle de stock, se retornará un header llamado x-version, el cual tendrá un valor entero (de tipo long) que representará la versión actual de /stock/.
Este header debe ser enviado al utilizar recursos que modifiquen el stock de los User Products (PUT /stock/type/selling_address y PUT /stock/type/seller_warehouse ).
Si no se envía, retornará un bad request (status code: 400).
Adicionalmente, en caso de que la versión enviada no sea la última, se retornará un conflict (status code: 409).
En el caso de una respuesta con código 409, se debe consultar nuevamente el stock para obtener la versión actualizada del header x-version.


Gestionar stock
La gestión y actualización de stock varía según la configuración del seller y la convivencia entre los modelos de logística. A continuación, se describen los diferentes escenarios y las recomendaciones para actualizar el stock de manera adecuada:

Stock sin multi origen activo:
Se debe utilizar el método PUT en el endpoint /items para actualizar el stock en available_quantity. En este caso, Mercado Libre sincronizará automáticamente el stock de todos los ítems asociados al mismo user_product_id.

Stock con convivencia Full/Flex sin multi origen activo (ubicaciones: meli_facility y selling_address):
Stock distribuido (aplica a MLA y MLC):
Los sellers pueden gestionar el stock de Flex de forma independiente. Para ello, deben actualizar el stock a través del endpoint:

PUT user-products/stock/type/selling_address

Para más detalles, consulta la documentación: Gestión de stock en convivencia Full y Flex.

Sin stock distribuido (resto de sites que operan con Full y Flex):
En estos casos, los vendedores no tienen la posibilidad de actualizar el stock de Flex de manera independiente.

Stock Multi Origen con convivencia Full/Flex:
Los vendedores habilitados para Multi Origen (warehouse_management) deben actualizar el stock de Flex a través del endpoint:

PUT /user-products/$USER_PRODUCT_ID/stock/type/seller_warehouse

Para más información, consulta la documentación: Gestión de stock por ubicación.

El vendedor podrá asociar la logística de Flex a múltiples depósitos desde su cuenta de Mercado Libre.

Nota:

Tengan en cuenta estos puntos:
- El stock de Full seguirá siendo gestionado por Mercado Libre;
- La logística de Flex podrá coexistir con Full en múltiples depósitos designados por el seller;
- El seller podrá configurar en qué depósitos desea activar Flex;
- El vendedor sigue necesitando configurar su capacidad de envío para Flex .

Stock en múltiples ubicaciones del seller (Multi Origen):
Los sellers habilitados para Multi Origen deben actualizar el stock a través del endpoint:

PUT /user-products/$USER_PRODUCT_ID/stock/type/seller_warehouse

Para más información, consulta la documentación: Gestión de stock por ubicación.

User Products
Importante:
Podrás realizar pruebas al solicitar la ambientación de tus usuarios de TEST con el siguiente formulario.
User Product (UP) es un nuevo concepto dentro de Mercado Libre que tiene como objetivo permitir al vendedor la elección de diferentes condiciones de venta para cada variante de un mismo producto.

En el modelo anterior de publicaciones de un vendedor, es posible crear variantes que agrupan diferentes opciones del mismo producto, por ejemplo una camisa en varios colores o tallas. Estas variantes permiten ofrecer productos relacionados dentro de una misma publicación. Sin embargo, este modelo tiene varias limitaciones:

No es posible establecer diferentes precios por variante.
No es posible configurar diferentes formas de entrega por variantes.
No es posible aplicar promociones o cuotas de pago específicas a una variante y no a otras.

Nuestro objetivo es adaptar un nuevo modelo que permita resolver estos problemas y unificar la experiencia, desacoplando las condiciones de venta para permitir diferencias por cada variante y así escalar las publicaciones.
A partir de esto, surge la idea de crear "User Products" (Productos de Usuario), donde las iniciativas a trabajar serán:

Precio por variación.
Stock distribuido.
Stock multi origen.
Este enfoque permitirá ofrecer una mayor flexibilidad en la configuración de publicaciones, permitiendo precios y gestión de stock específicos para cada variante, lo que mejorará la experiencia del comprador y la eficiencia en las operaciones de venta.


Conceptos importantes
Para comprender el modelo de User Product (UP), es fundamental tener en cuenta los siguientes conceptos:

Ítem:
Es la representación de la publicación de un producto que un comprador visualiza en la plataforma.
Contiene información relativa a condiciones de venta (precio, cuotas, etc).
Cada ítem tiene un identificador único (item_id) asociado.

User Product (UP):
Representa un producto físico que un vendedor posee y que oferta a través de la plataforma.
Un UP describe al producto de la manera más específica posible (a nivel de variación).
Cada UP tiene un identificador único (user_product_id) asignado automáticamente por el sistema.
Puede estar asociado a uno o más ítems. ej. un iphone rojo (el UP) puede estar en el item1 en 3 cuotas y en el item2 con otro precio distinto.
Todo UP podrá visualizarse en Mercado Libre a través de una User Products Page (UPP).

Familia:
Se autogenera en base a la información de los productos.
Cada UP pertenece a una familia (family_id), y cada familia agrupa a varios UPs.
Los ítems de la misma familia van a tener el mismo family_name y van a ser representados como pickers diferentes en la UPP. Los pickers son las opciones que se le ofrece a un buyer para comprar un producto, incluyendo diferentes condiciones de venta y atributos, por ejemplo, el color.
La modificación de los ítems mediante el PUT al recurso /items que refiere a características del User Product se replicará por Mercado Libre de manera asíncrona en todos los ítems asociados al mismo User Product. Los campos del ítem que se sincronizan son:
title
family_name
attributes
pictures
domain_id
catalog_product_id
condition
available_quantity
Para ítems de moda, la guía de talles va a ser compartida por la variación (User products) y sus condiciones de venta (ítems).

A continuación, para ejemplificar los conceptos antes mencionados, presentamos un comparativo entre una publicación en el modelo anterior vs el endgame con User Products.



Con base en el nuevo modelo, presentamos un ejemplo para una familia y su composición tanto en UP como en sus ítems y condiciones de venta:




Nota:
Nota: Para conocer cómo gestionar el stock acceda a la documentación de “Stock distribuido”.

FAQs
Precio por variación
¿Qué tipo de integradores deben adaptar sus desarrollos a esta iniciativa?

La iniciativa de Precio por variación y UPtin aplica a todos los integradores que publican, sincronizan o inclusive muestran listado de publicaciones para los vendedores. La iniciativa de Stock Distribuido y Multiorigen aplica para todos los vendedores que publican, sincronizan o toman información de las órdenes y envíos.


¿Qué impacto tendré en caso de no implementar la iniciativa?

Una vez que los sellers sean activados para comenzar a publicar bajo el nuevo modelo de Precio por Variació, en caso de que el integrador no esté adaptado a los cambios, no será posible publicar con el modelo anterior (informando title y array de variations).
Para los integradores que sincronizan ítems, actualizan stock, precio, o resguardan en sus bases de datos información sobre los items deben tener en cuenta la nueva estructura de modificación de stock (a nivel de UP) y además recibir notificaciones de cambios por migración de ítems para mantener consistencia de información en sus bases de datos.
Finalmente, para los integradores que listan publicaciones, deben considerar actualizar su front para adaptarse a la propuesta de valor que otorgará Mercado Libre con esta iniciativa. Es decir, agrupar los ítems por familia, por user product y además (en casos de publicar o modificar) permitir que se establezcan diferentes condiciones de venta para cada variación.


¿Cómo puedo identificar los sellers que ya se encuentran bajo el nuevo modelo de Precio por Variación?

A través del tag "user_product_seller" en la API /users.


¿Cómo puedo identificar los ítems que ya se encuentran en el modelo de Precio por Variación?

Validando si el ítem cuenta con family_name distinto a null. Esto sucederá en:

Ítems/Live Listings (LL) que ya pasaron el proceso de UPtin.
Nuevos ítems (NOLs) que fueron publicados a partir de que al seller se le asignó el tag "user_product_seller".

¿Los ítems de catálogo contarán con el tag user_product_listing = true?

No.


¿Cómo puedo probar el flujo de User Products?

Para probar los nuevos flujos, solicitamos que lo hagan a través de este formulario. Cada 7 días, activaremos estos nuevos usuarios.


¿Todos los vendedores serán habilitados para trabajar con precio por variaciones?

En el endgame, sí, todos los sellers estarán habilitados para publicar utilizarlo. A partir de octubre de 2024 los sellers se irán habilitando de manera progresiva hasta llegar al 100% de sellers en 2025.


¿Todos los ítems contarán con user_product_id, family_id y family_name?

Previo a la activación del tag "user_product_seller": los Live Listing contarán con user_product_id y no tendrán family_name. La relación de user_product_id y item_id será 1:1.
Posterior a la activación del tag "user_product_seller": se realizará un proceso de unificación para ítems mono-variantes y sin variantes, con la finalidad de agrupar los ítems que deberían pertenecer al mismo user_product_id, permitiendo que un user_product_id esté asociado a 1 o más ítems. Posterior a la unificación, los ítems contarán con el atributo family_name.
Cuando el seller decide realizar migrar un ítem multivariante al nuevo modelo (UPtin). En dicho caso, los nuevos ítems generados estarán asociados al mismo user_product_id y también contarán con family_name.

¿Hasta cuando el seller podrá publicar en el modelo viejo?

Hasta la activación del tag "user_product_seller". A partir de la activación, los nuevos ítems deberán ser creados bajo el nuevo modelo.


¿Existe algún endpoint para listar todos las familias de un seller?

No, actualmente no existe.


¿Cómo puedo obtener todos los ítems que corresponden a una misma familia?

Realizando las siguientes peticiones:

GET a /items para obtener el user_product_id
GET a /user-products/$USER_PRODUCT_ID para obtener el family_id
GET a /sites/$SITE_ID/user-products-families/$FAMILY_ID para obtener todos los User Products asociados a una familia
GET a /users/$SELLER_ID/items/search?user_product_id=$USER_PRODUCT_ID para obtener todos los ítems asociados a un user product. Se pueden enviar varios user_products_ids en el parámetro en forma de lista, ejemplo: GET /users/$SELLER_ID/items/search?user_product_id=MLAU1234,MLAU12345

¿De qué tamaño debe ser el family_name ingresado por el vendedor durante la publicación?

El family_name que podrá ingresar deberá ser menor o igual al “max_title_length” del dominio.


¿Es posible actualizar el family_name?

Sí, únicamente cuando ninguna de las condiciones de venta asociadas al User Product tenga ventas. Ten en cuenta de que en caso de que un ítem esté asociado a un UP con varios ítems, el family_name será posible actualizarlo y se sincronizará con todos los ítems del UP.


Al alterar la condición de venta de un User Product, ¿se va a alterar también su family_name?

No debería ser alterado, ya que el family_name no está relacionado con las condiciones de venta (por ejemplo, precio, tipo de listado).


¿El family_name será gestionado por el integrador, correcto? Es decir, ¿Meli no va a cambiar el valor de este campo?

Sí, es responsabilidad del vendedor/integrador. Sólo en el caso de UPtin Mercado Libre creará el family_name al artículo.


¿Puedo publicar con atributos tipo custom en el modelo de Precio por Variación?

Sí, se puede publicar sumando el atributo, ejemplo:


{
	"attributes": [
		{
			"name": "my-custom-attribute-name",
			"value_name":"my-custom-attribute-value"
		}
	]
}

¿El recurso /categories continuará funcionando igual para que podamos consultar los atributos y sus tags? Por ejemplo, allow_variations y variation_attribute.

Sí, incluso, podrás tomar como referencia (no regla) estos atributos para entender cuál será el atributo llevado para la completitud del family_name de la publicación.


¿Será posible enviar el array de variations después de la activación de un seller para trabajar con Precio por Variación?

No, no se podrá enviar el array, porque cada una de las variaciones van a ser User Products diferentes.


UPtin
¿Los ítems que se encuentren en el modelo anterior migrarán de manera automática al nuevo modelo?

Una vez que al seller se le active el modelo de Precio por Variación (cuente con el tag "user_product_seller), los ítems sin variantes serán migrados de manera automática por Mercado Libre hacía el nuevo modelo.


¿Todos los ítems son candidatos a migrar al nuevo modelo de Precio por Variación?

No, es necesario utilizar el endpoint de elegibilidad para validar si es posible migrar el ítem.


¿Cuándo el seller migre una publicación con 3 variantes del modelo actual al modelo User Products, ¿Cómo será enviada la notificación de creación?

Vas a a recibir una notificación por cada ítem creado a través del tópico de ítems. EI, el ítem antiguo quedará con el status closed y cada publicación nueva creada tendrá el tag “variations_migration_uptin”.


¿Qué pasará con la información de las ventas de las publicaciones antiguas?

El campo sold quantity reflejará las mismas ventas que el sold quantity de la variante, sin embargo las ordenes viejas quedarán asociadas al item_id viejo.



Stock distribuido y multiorigen
¿Cómo convivirá el nuevo y viejo mundo?

Cuando un vendedor se configura para multiorigen, todos los ítems pasan a gestionarse como de multiorigen también, no hay distinción entre viejo modelo y nuevo modelo.


¿El mismo anuncio podrá estar en más de un almacén (stock_location) del seller?

Sí, para los vendedores que tengan activo Multiorigen (tag warehouse_management) podrán distribuir el stock en sus diferentes stock_location. Conoce más sobre cómo distribuir stock en la documentación de Stock Multiorigen.


¿Una vez que el seller es encendido a multiorigen, cómo se debe distribuir el stock para publicaciones que se encuentran en el modelo antiguo?

Una vez que se prenda el seller a multiorigen el stock debedeve ser gestionado con el PUT a seller_warehouse.
