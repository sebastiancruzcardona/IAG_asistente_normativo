"""
Construcción del corpus documental del RAG.

Código migrado del prototipo prototipo_asistente_normativo_corte2.ipynb.
Elementos de la clase 7: documentos, limpieza, fragmentación por ventanas y embeddings. 
Elementos de la clase 8: validación del índice, huella, identificador del corpus y 
carga en Supabase. 

Solo se adaptó necesario para ejecutar desde la 
aplicación (sistema.preparar()):

- Los documentos se leen de FUENTES en memoria; no se escriben archivos .md.
- El índice (registros, vectores y configuración) no se guarda en un ZIP, sino que
  se serializa en memoria con los mismos bytes para calcular la misma huella.
- Antes de construir, hay_cambios() compara FUENTES y los parámetros con el
  corpus guardado en Supabase. Si no cambiaron, no se modifica nada.
- Una versión nueva se comparte (corpus_compartidos, migración 003) y
  actualiza CORPUS_ID y EMBEDDINGS_REVISION en app/.env.
"""

import hashlib, json, os, re
from io import BytesIO

import numpy as np

# ---------- Parámetros del prototipo (clases 7 y 8) ----------
MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CORPUS_BASE = "asistente_normativo"
VERSION = "1.0-implementacion"
# Estrategia con la que se generó el corpus actual (evidencias/Clase_09_Evidencia_Evaluacion_RAG.json).
# fragmentar() conserva la rama "parrafos" del prototipo, pero no se usa
ESTRATEGIA = "ventanas"

# Límites de Tokens
MAX_TOKENS = 95       # Presupuesto del fragmento completo, incluido el encabezado.
SOLAPAMIENTO = 17    # Tokens repetidos entre ventanas de un mismo bloque.

# Modelo y tokenizador. Se cargan en construir(), solo si hay cambios
modelo = tokenizador = None

# Documentos del corpus (clase 7, celda "Los documentos del corpus").
# Cambiar este texto genera una versión nueva del corpus al arrancar la app.
FUENTES = {
    "constitucion_politica.md": """# CONSTITUCION POLITICA DE COLOMBIA

## Artículo 1

Colombia   es un Estado social de derecho, organizado en forma de República unitaria, descentralizada, con autonomía de sus entidades territoriales, democrática, participativa y pluralista, fundada en el respeto de la dignidad humana, en el trabajo y la solidaridad de las personas que la integran y en la prevalencia del interés general.

## Artículo 2

Son fines esenciales del Estado: servir a la comunidad, promover la prosperidad general y garantizar la efectividad de los principios, derechos y deberes consagrados en la Constitución; facilitar la participación de todos en las decisiones que los afectan y en la vida económica, política, administrativa y cultural de la Nación; defender la independencia nacional, mantener la integridad territorial y asegurar la convivencia pacifica y la vigencia de un orden justo.


Las autoridades de la República están instituidas para proteger a todas las personas
residentes en Colombia, en su vida, honra, bienes, creencias, y demás derechos y
libertades, y para asegurar el cumplimiento de los deberes sociales del Estado y de los particulares.

## Artículo 3

La soberanía reside exclusivamente en el pueblo, del cual emana el poder público. El pueblo la ejerce en forma directa o por medio de sus representantes, en los términos que la Constitución establece.

## Artículo 4

La Constitución es norma de normas. En todo caso de incompatibilidad entre la Constitución y la ley u otra norma jurídica, se aplicarán las disposiciones
constitucionales.

Es deber   de los nacionales y de los extranjeros en Colombia acatar la Constitución y las leyes, y respetar y obedecer a las autoridades.

## Artículo 5

El Estado reconoce, sin discriminación alguna, la primacía de los derechos
inalienables de la persona y ampara a la familia como institución básica de la sociedad.

## Artículo 6

Los particulares sólo son responsables ante las autoridades por infringir la
Constitución y las leyes. Los servidores públicos lo son por la misma causa y por
omisión o extralimitación en el ejercicio de sus funciones.

## Artículo 7

El Estado reconoce y protege la diversidad étnica y cultural de la Nación
colombiana.

## Artículo 8

Es obligación del Estado y de las personas proteger las riquezas culturales y
naturales de la Nación.

## Artículo 9

Las relaciones exteriores del Estado se fundamentan en la soberanía
nacional, en el respeto a la autodeterminación de los pueblos y en el reconocimiento de
los principios del derecho internacional aceptados por Colombia.
De igual manera, la política exterior de Colombia se orientará hacia la
integración latinoamericana y del Caribe.

## Artículo 10

El castellano es el idioma oficial de Colombia. Las lenguas y dialectos de los
grupos étnicos son también oficiales en sus territorios. La enseñanza que se imparta
en las comunidades con tradiciones lingüísticas propias será bilingüe.

## Artículo 11

El derecho a la vida es inviolable. No habrá pena de muerte.

## Artículo 12

Nadie será sometido a desaparición forzada, a torturas ni a tratos o penas
crueles, inhumanos o degradantes.

## Artículo 13

Todas las personas nacen libres e iguales ante la ley, recibirán la misma
protección y trato de las autoridades y gozarán de los mismos derechos, libertades y
oportunidades sin ninguna discriminación por razones de sexo, raza, origen nacional o
familiar, lengua, religión, opinión política o filosófica.
El Estado promoverá las condiciones para que la igualdad sea real y efectiva y adoptara
medidas en favor de grupos discriminados o marginados.
El Estado protegerá especialmente a aquellas personas que por su condición
económica, física o mental, se encuentren en circunstancia de debilidad manifiesta y
sancionará los abusos o maltratos que contra ellas se cometan.

## Artículo 14

Toda persona tiene derecho al reconocimiento de su personalidad jurídica.

## Artículo 15

Todas las personas tienen derecho a su intimidad personal y familiar y a su
buen nombre, y el Estado debe respetarlos y hacerlos respetar. De igual modo, tienen
derecho a conocer, actualizar y rectificar las informaciones que se hayan recogido sobre
ellas en bancos de datos y en archivos de entidades públicas y privadas.
En la recolección, tratamiento y circulación de datos se respetarán la libertad y demás
garantías consagradas en la Constitución.
La correspondencia y demás formas de comunicación privada son inviolables. Sólo
pueden ser interceptadas o registradas mediante orden judicial, en los casos y con las
formalidades que establezca la ley.
Para efectos tributarios o judiciales y para los casos de inspección, vigilancia e
intervención del Estado podrá exigirse la presentación de libros de contabilidad y demás
documentos privados, en los términos que señale la ley.

## Artículo 16

Todas las personas tienen derecho al libre desarrollo de su personalidad
sin más limitaciones que las que imponen los derechos de los demás y el orden jurídico.

## Artículo 17

Se prohiben la esclavitud, la servidumbre y la trata de seres humanos en
todas sus formas.

## Artículo 18

Se garantiza la libertad de conciencia. Nadie será molestado por razón de sus
convicciones o creencias ni compelido a revelarlas ni obligado a actuar contra su
conciencia.

## Artículo 19

Se garantiza la libertad de cultos. Toda persona tiene derecho a profesar
libremente su religión y a difundirla en forma individual o colectiva.
Todas las confesiones religiosas e iglesias son igualmente libres ante la ley.

## Artículo 20

Se garantiza a toda persona la libertad de expresar y difundir su
pensamiento y opiniones, la de informar y recibir información veraz e imparcial, y la de
fundar medios masivos de comunicación.
Estos son libres y tienen responsabilidad social. Se garantiza el derecho a la
rectificación en condiciones de equidad. No habrá censura.

## Artículo 21

Se garantiza el derecho a la honra. La ley señalará la forma de su
protección.

## Artículo 22

La paz es un derecho y un deber de obligatorio cumplimiento.

## Artículo 23

Toda persona tiene derecho a presentar peticiones respetuosas a las
autoridades por motivos de interés general o particular y a obtener pronta resolución. El
legislador podrá reglamentar su ejercicio ante organizaciones privadas para garantizar
los derechos fundamentales.

## Artículo 24

Todo colombiano, con las limitaciones que establezca la ley, tiene derecho
a circular libremente por el territorio nacional, a entrar y salir de él, y a permanecer y
residenciarse en Colombia.

## Artículo 25

El trabajo es un derecho y una obligación social y goza, en todas sus
modalidades, de la especial protección del Estado. Toda persona tiene derecho a un
trabajo en condiciones dignas y justas.

## Artículo 26

Toda persona es libre de escoger profesión u oficio. La ley podrá exigir
títulos de idoneidad. Las autoridades competentes inspeccionaran y vigilaran el ejercicio
de las profesiones. Las ocupaciones, artes y oficios que no exijan formación académica
son de libre ejercicio, salvo aquellas que impliquen un riesgo social.
Las profesiones legalmente reconocidas pueden organizarse en colegios. La estructura
interna y el funcionamiento de estos deberán ser democráticos.
La ley podrá asignarles funciones públicas y establecer los debidos controles.

## Artículo 27

El Estado garantiza las libertades de enseñanza, aprendizaje, investigación
y cátedra.

## Artículo 28

Toda persona es libre. Nadie puede ser molestado en su persona o familia,
ni reducido a prisión o arresto, ni detenido, ni su domicilio registrado, sino en virtud de
mandamiento escrito de autoridad judicial competente, con las formalidades legales y
por motivo previamente definido en la ley.
La persona detenida preventivamente será puesta a disposición del juez competente
dentro de las treinta y seis horas siguientes, para que éste adopte la decisión
correspondiente en el término que establezca la ley. En ningún caso podrá haber
detención, prisión ni arresto por deudas, ni penas y medidas de seguridad
imprescriptibles.

## Artículo 29

El debido proceso se aplicará a toda clase de actuaciones judiciales y
administrativas.
Nadie podrá ser juzgado sino conforme a leyes preexistentes al acto que se le imputa,
ante juez o tribunal competente y con observancia de la plenitud de las formas propias
de cada juicio.
En materia penal, la ley permisiva o favorable, aun cuando sea posterior, se aplicará de
preferencia a la restrictiva o desfavorable.
Toda persona se presume inocente mientras no se la haya declarado judicialmente
culpable. Quien sea sindicado tiene derecho a la defensa y a la asistencia de un
abogado escogido por el, o de oficio, durante la investigación y el juzgamiento; a un
debido proceso publico sin dilaciones injustificadas; a presentar pruebas y a controvertir
las que se alleguen en su contra; a impugnar la sentencia condenatoria, y a no ser
juzgado dos veces por el mismo hecho.
Es nula, de pleno derecho, la prueba obtenida con violación del debido proceso.

## Artículo 30

Quien estuviere privado de su libertad, y creyere estarlo ilegalmente, tiene
derecho a invocar ante cualquier autoridad judicial, en todo tiempo, por si o por
interpuesta persona, el Habeas Corpus, el cual debe resolverse en el término de treinta
y seis horas.

## Artículo 31

Toda sentencia judicial podrá ser apelada o consultada, salvo las
excepciones que consagre la ley.
El superior no podrá agravar la pena impuesta cuando el condenado sea apelante
único.

## Artículo 32

El delincuente sorprendido en flagrancia podrá ser aprehendido y llevado
ante el juez por cualquier persona. Si los agentes de la autoridad lo persiguieren y se
refugiare en su propio domicilio, podrán penetrar en él, para el acto de la aprehensión;
si se acogiere a domicilio ajeno, deberá preceder requerimiento al morador.

## Artículo 33

Nadie podrá ser obligado a declarar contra si mismo o contra su cónyuge,
compañero permanente o parientes dentro del cuarto grado de consanguinidad,
segundo de afinidad o primero civil.

## Artículo 34

Se prohiben las penas de destierro, prisión perpetua y confiscación.
No obstante, por sentencia judicial, se declarará extinguido el dominio sobre los bienes
adquiridos mediante enriquecimiento ilícito, en perjuicio del Tesoro Público o con grave
deterioro de la moral social.

## Artículo 35

Se prohibe la extradición de colombianos por nacimiento. No se concederá
la extradición de extranjeros por delitos políticos o de opinión.
Los colombianos que hayan cometido delitos en el exterior, considerados como tales en
la legislación nacional, serán procesados y juzgados en Colombia.

## Artículo 36

Se reconoce el derecho de asilo en los términos previstos en la ley.

## Artículo 37

Toda parte del pueblo puede reunirse y manifestarse pública y
pacíficamente. Sólo la ley podrá establecer de manera expresa los casos en los cuales
se podrá limitar el ejercicio de este derecho.

## Artículo 38

Se garantiza el derecho de libre asociación para el desarrollo de las
distintas actividades que las personas realizan en sociedad.

## Artículo 39

Los trabajadores y empleadores tienen derecho a constituir sindicatos o
asociaciones, sin intervención del Estado. Su reconocimiento jurídico se producirá con
la simple inscripción del acta de constitución.
La estructura interna y el funcionamiento de los sindicatos y organizaciones sociales y
gremiales se sujetarán al orden legal y a los principios democráticos.
La cancelación o la suspensión de la personería jurídica sólo procede por vía judicial.
Se reconoce a los representantes sindicales el fuero y las demás garantías necesarias
para el cumplimiento de su gestión.
No gozan del derecho de asociación sindical los miembros de la Fuerza Pública.

## Artículo 40

Todo ciudadano tiene derecho a participar en la conformación, ejercicio y
control del poder político. Para hacer efectivo este derecho puede:
1. Elegir y ser elegido.
2. Tomar parte en elecciones, plebiscitos, referendos, consultas populares y otras
formas de participación democrática.
3. Constituir partidos, movimientos y agrupaciones políticas sin limitación alguna: formar
parte de ellos libremente y difundir sus ideas y programas.
4. Revocar el mandato de los elegidos en los casos y en la forma que establecen la
Constitución y la ley.
5. Tener iniciativa en las corporaciones públicas.
6. Interponer acciones públicas en defensa de la Constitución y de la ley.
7. Acceder al desempeño de funciones y cargos públicos, salvo los colombianos, por
nacimiento o por adopción, que tengan doble nacionalidad. La ley reglamentará esta
excepción y determinará los casos a los cuales ha de aplicarse.
Las autoridades garantizarán la adecuada y efectiva participación de la mujer en los
niveles decisorios de la Administración Pública.

## Artículo 41

En todas las instituciones de educación, oficiales o privadas, serán
obligatorios el estudio de la Constitución y la Instrucción Cívica. Así mismo se
fomentarán prácticas democráticas para el aprendizaje de los principios y valores de
la participación ciudadana. El Estado divulgará la Constitución.

## Artículo 42

La familia es el núcleo fundamental de la sociedad. Se constituye por vínculos naturales 
o jurídicos, por la decisión libre de un hombre y una mujer de contraer matrimonio 
o por la voluntad responsable de conformarla.
El Estado y la sociedad garantizan la protección integral de la familia. La ley podrá
determinar el patrimonio familiar inalienable e inembargable.
La honra, la dignidad y la intimidad de la familia son inviolables.
Las relaciones familiares se basan en la igualdad de derechos y deberes de la pareja y
en el respeto recíproco entre todos sus integrantes.
Cualquier forma de violencia en la familia se considera destructiva de su armonía y
unidad, y será sancionada conforme a la ley.
Los hijos habidos en el matrimonio o fuera de él, adoptados o procreados naturalmente
o con asistencia científica, tienen iguales derechos y deberes.
La ley reglamentará la progenitura responsable.
La pareja tiene derecho a decidir libre y responsablemente el número de sus hijos, y
deberá sostenerlos y educarlos mientras sean menores o impedidos.
Las formas del matrimonio, la edad y capacidad para contraerlo, los deberes y derechos
de los cónyuges, su separación y la disolución del vínculo, se rigen por la ley civil.
Los matrimonios religiosos tendrán efectos civiles en los términos que establezca la ley.
Los efectos civiles de todo matrimonio cesarán por divorcio con arreglo a la ley civil.
También tendrán efectos civiles las sentencias de nulidad de los matrimonios religiosos
dictadas por las autoridades de la respectiva religión, en los términos que establezca la
ley.
La ley determinará lo relativo al estado civil de las personas y los consiguientes
derechos y deberes.

## Artículo 43

La mujer y el hombre tienen iguales derechos y oportunidades. La mujer no
podrá ser sometida a ninguna clase de discriminación. Durante el embarazo y después
del parto gozará de especial asistencia y protección del Estado, y recibirá de este
subsidio alimentario si entonces estuviere desempleada o desamparada.
El Estado apoyará de manera especial a la mujer cabeza de familia.

## Artículo 44

Son derechos fundamentales de los niños: la vida, la integridad física, la
salud y la seguridad social, la alimentación equilibrada, su nombre y nacionalidad, tener
una familia y no ser separados de ella, el cuidado y amor, la educación y la cultura, la
recreación y la libre expresión de su opinión. Serán protegidos contra toda forma de
abandono, violencia física o moral, secuestro, venta, abuso sexual, explotación laboral o
económica y trabajos riesgosos. Gozarán también de los demás derechos consagrados
en la Constitución, en las leyes y en los tratados internacionales ratificados por
Colombia.
La familia, la sociedad y el Estado tienen la obligación de asistir y proteger al niño para
garantizar su desarrollo armónico e integral y el ejercicio pleno de sus derechos.
Cualquier persona puede exigir de la autoridad competente su cumplimiento y la
sanción de los infractores. Los derechos de los niños prevalecen sobre los derechos de
los demás.

## Artículo 45

El adolescente tiene derecho a la protección y a la formación integral.
El Estado y la sociedad garantizan la participación activa de los jóvenes en los
organismos públicos y privados que tengan a cargo la protección, educación y progreso
de la juventud.

## Artículo 46

El Estado, la sociedad y la familia concurrirán para la protección y la
asistencia de las personas de la tercera edad y promoverán su integración a la vida
activa y comunitaria.
El Estado les garantizará los servicios de la seguridad social integral y el subsidio
alimentario en caso de indigencia.

## Artículo 47

El Estado adelantará una política de previsión, rehabilitación e integración
social para los disminuidos físicos, sensoriales y psíquicos, a quienes se prestará la
atención especializada que requieran.

## Artículo 48

La Seguridad Social es un servicio público de carácter obligatorio que se
prestará bajo la dirección, coordinación y control del Estado, en sujeción a los principios
de eficiencia, universalidad y solidaridad, en los términos que establezca la Ley.
Se garantiza a todos los habitantes el derecho irrenunciable a la Seguridad Social.
El Estado, con la participación de los particulares, ampliara progresivamente la
cobertura de la Seguridad Social que comprenderá la prestación de los servicios en la
forma que determine la Ley.
La Seguridad Social podrá ser prestada por entidades públicas o privadas, de
conformidad con la ley.
No se podrán destinar ni utilizar los recursos de las instituciones de la Seguridad Social
para fines diferentes a ella.
La ley definirá los medios para que los recursos destinados a pensiones mantengan su
poder adquisitivo constante.

## Artículo 49

La atención de la salud y el saneamiento ambiental son servicios públicos
a cargo del Estado. Se garantiza a todas las personas el acceso a los servicios de
promoción, protección y recuperación de la salud.
Corresponde al Estado organizar, dirigir y reglamentar la prestación de servicios de
salud a los habitantes y de saneamiento ambiental conforme a los principios de
eficiencia, universalidad y solidaridad. También, establecer las políticas para la
prestación de servicios de salud por entidades privadas, y ejercer su vigilancia y control.
Así mismo, establecer las competencias de la Nación, las entidades territoriales y los
particulares y determinar los aportes a su cargo en los términos y condiciones
señalados en la ley.
Los servicios de salud se organizarán en forma descentralizada, por niveles de atención
y con participación de la comunidad.
La ley señalará los términos en los cuales la atención básica para todos los habitantes
será gratuita y obligatoria.
Toda persona tiene el deber de procurar el cuidado integral de su salud y la de su
comunidad.

## Artículo 50

Todo niño menor de un año que no esté cubierto por algún tipo de
protección o de seguridad social, tendrá derecho a recibir atención gratuita en todas las
instituciones de salud que reciban aportes del Estado. La ley reglamentará la materia.

## Artículo 51

Todos los colombianos tienen derecho a vivienda digna. El Estado fijará las
condiciones necesarias para hacer efectivo este derecho y promoverá planes de
vivienda de interés social, sistemas adecuados de financiación a largo plazo y formas
asociativas de ejecución de estos programas de vivienda.

## Artículo 52

Se reconoce el derecho de todas las personas a la recreación, a la práctica
del deporte y al aprovechamiento del tiempo libre.
El Estado fomentará estas actividades e inspeccionará las organizaciones deportivas,
cuya estructura y propiedad deberán ser democráticas.

## Artículo 53

El Congreso expedirá el estatuto del trabajo. La ley correspondiente tendrá
en cuenta por lo menos los siguientes principios mínimos fundamentales:
Igualdad de oportunidades para los trabajadores; remuneración mínima vital y móvil,
proporcional a la cantidad y calidad de trabajo; estabilidad en el empleo;
irrenunciabilidad a los beneficios mínimos establecidos en normas laborales; facultades
para transigir y conciliar sobre derechos inciertos y discutibles; situación más favorable
al trabajador en caso de duda en la aplicación e interpretación de las fuentes formales
de derecho; primacía de la realidad sobre formalidades establecidas por los sujetos de
las relaciones laborales; garantía a la seguridad social, la capacitación, el
adiestramiento y el descanso necesario; protección especial a la mujer, a la maternidad
y al trabajador menor de edad.
El Estado garantiza el derecho al pago oportuno y al reajuste periódico de las pensiones
legales.
Los convenios internacionales del trabajo debidamente ratificados, hacen parte de la
legislación interna.
La ley, los contratos, los acuerdos y convenios de trabajo, no pueden menoscabar la
libertad, la dignidad humana ni los derechos de los trabajadores.

## Artículo 54

Es obligación del Estado y de los empleadores ofrecer formación y
habilitación profesional y técnica a quienes lo requieran. El Estado debe propiciar la
ubicación laboral de las personas en edad de trabajar y garantizar a los minusválidos el
derecho a un trabajo acorde con sus condiciones de salud.

## Artículo 55

Se garantiza el derecho de negociación colectiva para regular las
relaciones laborales, con las excepciones que señale la ley.
Es deber del Estado promover la concertación y los demás medios para la solución
pacífica de los conflictos colectivos de trabajo.

## Artículo 56

Se garantiza el derecho de huelga, salvo en los servicios públicos
esenciales definidos por el legislador.
La ley reglamentará este derecho.
Una comisión permanente integrada por el Gobierno, por representantes de los
empleadores y de los trabajadores, fomentará las buenas relaciones laborales,
contribuirá a la solución de los conflictos colectivos de trabajo y concertará las políticas
salariales y laborales. La ley reglamentará su composición y funcionamiento.

## Artículo 57

La ley podrá establecer los estímulos y los medios para que los
trabajadores participen en la gestión de las empresas.

## Artículo 58

Se garantizan la propiedad privada y los demás derechos adquiridos con
arreglo a las leyes civiles, los cuales no pueden ser desconocidos ni vulnerados por
leyes posteriores. Cuando de la aplicación de una ley expedida por motivo de utilidad
pública o interés social, resultaren en conflicto los derechos de los particulares con la
necesidad por ella reconocida, el interés privado deberá ceder al interés público o
social.
La propiedad es una función social que implica obligaciones. Como tal, le es inherente
una función ecológica.
El Estado protegerá y promoverá las formas asociativas y solidarias de propiedad.
Por motivos de utilidad pública o de interés social definidos por el legislador, podrá
haber expropiación mediante sentencia judicial e indemnización previa. Esta se fijará
consultando los intereses de la comunidad y del afectado. En los casos que determine
el legislador, dicha expropiación podrá adelantarse por vía administrativa, sujeta a
posterior acción contenciosa administrativa, incluso respecto del precio.
Con todo, el legislador, por razones de equidad, podrá determinar los casos en que no
haya lugar al pago de indemnización, mediante el voto favorable de la mayoría absoluta
de los miembros de una y otra Cámara. Las razones de equidad, así como los motivos
de utilidad pública o de interés social, invocados por el legislador, no serán
controvertibles judicialmente.

## Artículo 59

En caso de guerra y sólo para atender a sus requerimientos, la necesidad
de una expropiación podrá ser decretada por el Gobierno Nacional sin previa
indemnización.
En el expresado caso, la propiedad inmueble sólo podrá ser temporalmente ocupada,
para atender a las necesidades de la guerra, o para destinar a ella sus productos.
El Estado será siempre responsable por las expropiaciones que el Gobierno haga por si
o por medio de sus agentes.

## Artículo 60

El Estado promoverá, de acuerdo con la ley, el acceso a la propiedad.
Cuando el Estado enajene su participación en una empresa, tomara las medidas
conducentes a democratizar la titularidad de sus acciones y ofrecerá a sus trabajadores,
a las organizaciones solidarias y de trabajadores, condiciones especiales para acceder
a dicha propiedad accionaria. La ley reglamentará la materia.

## Artículo 61

El Estado protegerá la propiedad intelectual por el tiempo y mediante las
formalidades que establezca la ley;

## Artículo 62

El destino de las donaciones intervivos o testamentarias, hechas conforme
a la ley para fines de interés social, no podrá ser variado ni modificado por el legislador,
a menos que el objeto de la donación desaparezca. En este caso, la ley asignará el
patrimonio respectivo a un fin similar.
El Gobierno fiscalizará el manejo y la inversión de tales donaciones.

## Artículo 63

Los bienes de uso público, los parques naturales, las tierras comunales de
grupos étnicos, las tierras de resguardo, el patrimonio arqueológico de la Nación y los
demás bienes que determine la ley, son inalienables, imprescriptibles e inembargables.

## Artículo 64

Es deber del Estado promover el acceso progresivo a la propiedad de la
tierra de los trabajadores agrarios, en forma individual o asociativa, y a los servicios de
educación, salud, vivienda, seguridad social, recreación, crédito, comunicaciones,
comercialización de los productos, asistencia técnica y empresarial, con el fin de
mejorar el ingreso y calidad de vida de los campesinos.

## Artículo 65

La producción de alimentos gozará de la especial protección del Estado.
Para tal efecto, se otorgará prioridad al desarrollo integral de las actividades agrícolas,
pecuarias, pesqueras, forestales y agroindustriales, así como también a la construcción
de obras de infraestructura física y adecuación de tierras.
De igual manera, el Estado promoverá la investigación y la transferencia de tecnología
para la producción de alimentos y materias primas de origen agropecuario, con el
propósito de incrementar la productividad.

## Artículo 66

Las disposiciones que se dicten en materia crediticia podrán reglamentar
las condiciones especiales del crédito agropecuario, teniendo en cuenta los ciclos de las
cosechas y de los precios, como también los riesgos inherentes a la actividad y las
calamidades ambientales.

## Artículo 67

La educación es un derecho de la persona y un servicio público que tiene
una función social: con ella se busca el acceso al conocimiento, a la ciencia, a la
técnica, y a los demás bienes y valores de la cultura.
La educación formara al colombiano en el respeto a los derechos humanos, a la paz y a
la democracia; y en la practica del trabajo y la recreación, para el mejoramiento cultural,
científico, tecnológico y para la protección del ambiente.
El Estado, la sociedad y la familia son responsables de la educación, que será
obligatoria entre los cinco y los quince años de edad y que comprenderá como mínimo,
un año de preescolar y nueve de educación básica.
La educación será gratuita en las instituciones del Estado, sin perjuicio del cobro de
derechos académicos a quienes puedan sufragarlos.
Corresponde al Estado regular y ejercer la suprema inspección y vigilancia de la
educación con el fin de velar por su calidad, por el cumplimiento de sus fines y por la
mejor formación moral, intelectual y física de los educandos; garantizar el adecuado
cubrimiento del servicio y asegurar a los menores las condiciones necesarias para su
acceso y permanencia en el sistema educativo.
La Nación y las entidades territoriales participarán en la dirección, financiación y
administración de los servicios educativos estatales, en los términos que señalen la
Constitución y la ley.

## Artículo 68

Los particulares podrán fundar establecimientos educativos. La Ley
establecerá las condiciones para su creación y gestión.
La comunidad educativa participará en la dirección de las instituciones de educación.
La enseñanza estará a cargo de personas de reconocida idoneidad ética y pedagógica.
La Ley garantiza la profesionalización y dignificación de la actividad docente.
Los padres de familia tendrán derecho de escoger el tipo de educación para sus hijos
menores. En los establecimientos del Estado ninguna persona podrá ser obligada a
recibir educación religiosa.
Las integrantes de los grupos étnicos tendrán derecho a una formación que respete y
desarrolle su identidad cultural.
La erradicación del analfabetismo y la educación de personas con limitaciones físicas o
mentales, o con capacidades excepcionales, son obligaciones especiales del Estado.

## Artículo 69

Se garantiza la autonomía universitaria. Las universidades podrán darse
sus directivas y regirse por sus propios estatutos, de acuerdo con la ley.
La ley establecerá un régimen especial para las universidades del Estado.
El Estado fortalecerá la investigación científica en las universidades oficiales y privadas
y ofrecerá las condiciones especiales para su desarrollo.
El Estado facilitara mecanismos financieros que hagan posible el acceso de todas las
personas aptas a la educación superior.

## Artículo 70

El Estado tiene el deber de promover y fomentar el acceso a la cultura de
todos los colombianos en igualdad de oportunidades, por medio de la educación
permanente y la enseñanza científica, técnica, artística y profesional en todas las
etapas del proceso de creación de la identidad nacional.
La cultura en sus diversas manifestaciones es fundamento de la nacionalidad. El Estado
reconoce la igualdad y dignidad de todas las que conviven en el país. El Estado
promoverá la investigación, la ciencia, el desarrollo y la difusión de los valores culturales
de la Nación.

## Artículo 71

La búsqueda del conocimiento y la expresión artística son libres. Los
planes de desarrollo económico y social incluirán el fomento a las ciencias y, en
general, a la cultura. El Estado creará incentivos para personas e instituciones que
desarrollen y fomenten la ciencia y la tecnología y las demás manifestaciones culturales
y ofrecerá estímulos especiales a personas e instituciones que ejerzan estas
actividades.

## Artículo 72

El patrimonio cultural de la Nación está bajo la protección del Estado. El
patrimonio arqueológico y otros bienes culturales que conforman la identidad nacional,
pertenecen a la Nación y son inalienables, inembargables e imprescriptibles. La ley
establecerá los mecanismos para readquirirlos cuando se encuentren en manos de
particulares y reglamentará los derechos especiales que pudieran tener los grupos
étnicos asentados en territorios de riqueza arqueológica.

## Artículo 73

La actividad periodística gozará de protección para garantizar su libertad e
independencia profesional.

## Artículo 74

Todas las personas tienen derecho a acceder a los documentos públicos
salvo los casos que establezca la ley.
El secreto profesional es inviolable.

## Artículo 75

El espectro electromagnético es un bien público inenajenable e
imprescriptible sujeto a la gestión y control del Estado. Se garantiza la igualdad de
oportunidades en el acceso a su uso en los términos que fije la ley.
Para garantizar el pluralismo informativo y la competencia, el Estado intervendrá por
mandato de la ley para evitar las prácticas monopolísticas en el uso del espectro
electromagnético.

## Artículo 76

La intervención estatal en el espectro electromagnético utilizado para los
servicios de televisión, estará a cargo de un organismo de derecho público con
personería jurídica, autonomía administrativa, patrimonial y técnica, sujeto a un régimen
legal propio.
Dicho organismo desarrollará y ejecutará los planes y programas del Estado en el
servicio a que hace referencia el inciso anterior.

## Artículo 77

La dirección de la política que en materia de televisión determine la ley sin
menoscabo de las libertades consagradas en esta Constitución, estará a cargo del
organismo mencionado.
La televisión será regulada por una entidad autónoma del orden nacional, sujeta a un
régimen propio. La dirección y ejecución de las funciones de la entidad estarán a cargo
de una Junta Directiva integrada por cinco (5) miembros, la cual nombrará al director.
Los miembros de la Junta tendrán período fijo. El gobierno nacional designará dos de
ellos. Otro será escogido entre los representantes legales de los canales regionales de
televisión. La ley dispondrá lo relativo al nombramiento de los demás miembros y
regulará la organización y funcionamiento de la Entidad.

Parágrafo. Se garantizarán y respetarán la estabilidad y los derechos de los
trabajadores de Inravisión.

## Artículo 78

La ley regulará el control de calidad de bienes y servicios ofrecidos y
prestados a la comunidad, así como la información que debe suministrarse al público en
su comercialización.
Serán responsables, de acuerdo con la ley, quienes en la producción y en la
comercialización de bienes y servicios, atenten contra la salud, la seguridad y el
adecuado aprovisionamiento a consumidores y usuarios. El Estado garantizara la
participación de las organizaciones de consumidores y usuarios en el estudio de las
disposiciones que les conciernen. Para gozar de este derecho las organizaciones deben
ser representativas y observar procedimientos democráticos internos.

## Artículo 79

Todas las personas tienen derecho a gozar de un ambiente sano. La ley
garantizará la participación de la comunidad en las decisiones que puedan afectarlo.
Es deber del Estado proteger la diversidad e integridad del ambiente, conservar las
áreas de especial importancia ecológica y fomentar la educación para el logro de estos
fines.

## Artículo 80

El Estado planificará el manejo y aprovechamiento de los recursos
naturales, para garantizar su desarrollo sostenible, su conservación, restauración o
sustitución.
Además, deberá prevenir y controlar los factores de deterioro ambiental, imponer las
sanciones legales y exigir la reparación de los daños causados.
Así mismo, cooperará con otras naciones en la protección de los ecosistemas situados
en las zonas fronterizas.

## Artículo 81

Queda prohibida la fabricación, importación, posesión y uso de armas
químicas, biológicas y nucleares, así como la introducción al territorio nacional de
residuos nucleares y desechos tóxicos.
El Estado regulará el ingreso al país y la salida de él de los recursos genéticos, y su
utilización, de acuerdo con el interés nacional.

## Artículo 82

Es deber del Estado velar por la protección de la integridad del espacio
público y por su destinación al uso común, el cual prevalece sobre el interés particular.
Las entidades públicas participarán en la plusvalía que genere su acción urbanística y
regularán la utilización del suelo y del espacio aéreo urbano en defensa del interés
común.

## Artículo 83

Las actuaciones de los particulares y de las autoridades públicas deberán
ceñirse a los postulados de la buena fe, la cual se presumirá en todas las gestiones que
aquellos adelanten ante éstas.

## Artículo 84

Cuando un derecho o una actividad hayan sido reglamentados de manera
general, las autoridades públicas no podrán establecer ni exigir permisos, licencias o
requisitos adicionales para su ejercicio.

## Artículo 85

Son de aplicación inmediata los derechos consagrados en los artículos 11,
12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 26, 27, 28, 29, 30, 31, 33, 34, 37 y 40.

## Artículo 86

Toda persona tendrá acción de tutela para reclamar ante los jueces, en
todo momento y lugar, mediante un procedimiento preferente y sumario, por sí misma o
por quien actúe a su nombre, la protección inmediata de sus derechos constitucionales
fundamentales, cuando quiera que éstos resulten vulnerados o amenazados por la
acción o la omisión de cualquier autoridad pública.
La protección consistirá en una orden para que aquél respecto de quien se solicita la
tutela, actúe o se abstenga de hacerlo. El fallo, que será de inmediato cumplimiento,
podrá impugnarse ante el juez competente y, en todo caso, éste lo remitirá a la Corte
Constitucional para su eventual revisión.
Esta acción sólo procederá cuando el afectado no disponga de otro medio de defensa
judicial, salvo que aquella se utilice como mecanismo transitorio para evitar un perjuicio
irremediable.
En ningún caso podrán transcurrir más de diez días entre la solicitud de tutela y su
resolución.
La ley establecerá los casos en los que la acción de tutela procede Contra particulares
encargados de la prestación de un servicio público o cuya conducta afecte grave y
directamente el interés colectivo, o respecto de quienes el solicitante se halle en estado
de subordinación o indefensión.

## Artículo 87

Toda persona podrá acudir ante la autoridad judicial para hacer efectivo el
cumplimiento de una ley o un acto administrativo.
En caso de prosperar la acción, la sentencia ordenará a la autoridad renuente el
cumplimiento del deber omitido.

## Artículo 88

La ley regulará las acciones populares para la protección de los derechos e
intereses colectivos, relacionados con el patrimonio, el espacio, la seguridad y la
salubridad públicos, la moral administrativa, el ambiente, la libre competencia
económica y otros de similar naturaleza que se definen en ella.
También regulará las acciones originadas en los daños ocasionados a un número plural
de personas, sin perjuicio de las correspondientes acciones particulares.
Así mismo, definirá los casos de responsabilidad civil objetiva por el daño inferido a los
derechos e intereses colectivos.

## Artículo 89

Además de los consagrados en los artículos anteriores, la ley establecerá
los demás recursos, las acciones, y los procedimientos necesarios para que puedan
propugnar por la integridad del orden jurídico, y por la protección de sus derechos
individuales, de grupo o colectivos, frente a la acción u omisión de las autoridades
públicas.

## Artículo 90

El Estado responderá patrimonialmente por los daños antijurídicos que le
sean imputables, causados por la acción o la omisión de las autoridades públicas.
En el evento de ser condenado el Estado a la reparación patrimonial de uno de tales
daños, que haya sido consecuencia de la conducta dolosa o gravemente culposa de un
agente suyo, aquel deberá repetir contra éste.

## Artículo 91

En caso de infracción manifiesta de un precepto constitucional en
detrimento de alguna persona, el mandato superior no exime de responsabilidad al
agente que lo ejecuta.
Los militares en servicio quedan exceptuados de esta disposición. Respecto de ellos, la
responsabilidad recaerá únicamente en el superior que da la orden.

## Artículo 92

Cualquier persona natural o jurídica podrá solicitar de la autoridad
competente la aplicación de las sanciones penales o disciplinarias derivadas de la
conducta de las autoridades públicas.

## Artículo 93

Los tratados y convenios internacionales ratificados por el Congreso, que
reconocen los derechos humanos y que prohiben su limitación en los estados de
excepción, prevalecen en el orden interno. Los derechos y deberes consagrados en
esta Carta, se interpretarán de conformidad con los tratados internacionales sobre
derechos humanos ratificados por Colombia.

## Artículo 94

La enunciación de los derechos y garantías contenidos en la Constitución y
en los convenios internacionales vigentes, no debe entenderse como negación de otros
que, siendo inherentes a la persona humana, no figuren expresamente en ellos.
"""
}


# =====================================================================
# Clase 7. Lectura, limpieza y fragmentación
# =====================================================================

def cargar_modelo(revision):
    """
    Carga el modelo de embeddings con una revisión exacta (clase 7, punto 1).
    """
    global modelo, tokenizador

    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(MODELO_EMBEDDINGS, revision=revision, device="cpu")
    tokenizador = modelo.tokenizer


def contar_tokens(texto):
    """
    Recibe un texto y retorna un número entero con la cantidad real de
    tokens que el modelo procesará.

    - Añade los tokens especiales que el modelo necesita internamente,
      como marcadores de inicio o final.

    - Prohíbe recortar el texto automáticamente para detectar si un texto
      supera el límite, en lugar de perder información silenciosamente.
    """
    return len(tokenizador.encode(texto, add_special_tokens=True, truncation=False))


def leer_documentos():
    """
    Limpia los documentos de FUENTES y conserva sus metadatos (clase 7, punto 3).
    En el prototipo se leían de los archivos .md escritos en Colab; el texto y
    su huella son los mismos.
    """
    # Lista de diccionarios para guardar metadatos y texto limpio de cada archivo
    documentos = []

    # Recorrer en orden alfabético todos los documentos
    for nombre in sorted(FUENTES):
        # Archivo original
        original = FUENTES[nombre]

        # Limpiar dobles espacios en blanco o tabs, reemplazar por un solo espacio
        limpio = re.sub(r"[ \t]+", " ", original)

        # Reemplazar 3 o más saltos de línea por 2 saltos de línea (separación
        # normal entre párrafos) y eliminar espacios vacíos al inicio y final
        limpio = re.sub(r"\n{3,}", "\n\n", limpio).strip()

        # Guardar metadatos del documento (con identidad y procedencia)
        documentos.append({
            "document_id": nombre.removesuffix(".md"), # Nombre del archivo sin extensión
            "source": nombre, # Nombre completo con extensión
            "title": limpio.splitlines()[0].lstrip("# "), # Título quitando el # del md
            "version": VERSION,
            "source_hash": hashlib.sha256(
                original.encode("utf-8")
            ).hexdigest(), #  Hash del contenido original del archivo para versionado
            "texto": limpio,
        })

    return documentos


def ventanas(texto, limite):
    """
    Divide un texto en ventanas de tokens con solapamiento entre fragmentos.

    Args:
        texto: Texto que se desea fragmentar.
        limite: Máximo de tokens permitidos por ventana.

    Yields:
        Fragmentos de texto consecutivos, con un solapamiento de
        `SOLAPAMIENTO` tokens entre ventanas.
    """
    # Dividir el texto en tokens y devolver posición de inicio y final para c/u
    offsets = tokenizador(
        texto,
        add_special_tokens=False, # Sin tokens especiales, solo fragmentar contenido
        return_offsets_mapping=True # Para recuperar texto real usando posiciones
    )["offset_mapping"]

    # Validar tamaño de la ventana para garantizar avance en el texto
    if limite <= SOLAPAMIENTO:
        raise ValueError("El encabezado deja muy poco espacio para el contenido.")

    # Recorrer los tokens con salto = límite (95) - Solapamiento (17) = 78
    # Esto garantiza el tamaño de cada ventana y el solapamiento
    for inicio in range(0, len(offsets), limite - SOLAPAMIENTO):
        # Fin de la ventana. Evitar acceder a tokens que no existen en la última ventana.
        fin = min(inicio + limite, len(offsets))
        # Generar una ventana cada vez. Extraer desde el primer hasta el último caracter del token
        yield texto[offsets[inicio][0]:offsets[fin - 1][1]].strip()

        # Detener el for al alcanzar el último token
        if fin == len(offsets):
            break


def fragmentar(estrategia, documentos):
    """
    Fragmenta los documentos según la estrategia indicada y genera los
    registros necesarios para su posterior indexación.

    Args:
        estrategia: Estrategia de fragmentación, `ventanas` o `parrafos`.
        documentos: Documentos limpios de leer_documentos().

    Returns:
        Lista de diccionarios de fragmentos con sus metadatos, sección, número
        de tokens y contenido.
    """
    # Lista de diccionarios para almacenar los fragmentos y sus metadatos
    registros = []

    # Procesar cada documento leído y limpiado
    for documento in documentos:

        # Enumerar desde 1 todos los títulos de nivel 2 (##) o títulos de sección
        for numero, bloque in enumerate(re.split(r"(?m)^## ", documento["texto"])[1:], 1):
            # seccion: título de la sección, cuerpo: texto de la sección
            seccion, cuerpo = bloque.split("\n", 1) # Solo una división en \n

            # encabezado: titulo_documento / titulo_seccion
            encabezado = documento["title"] + " / " + seccion + "\n"

            # Tokens disponibles luego de encabezado y 2 de margen
            limite = MAX_TOKENS - contar_tokens(encabezado) - 2

            # Qué se va a fragmentar según la estrategia
            partes = [cuerpo] if estrategia == "ventanas" else re.split(r"\n\s*\n", cuerpo.strip())

            # Procesar cada bloque (ventanas) o párrafo (párrafos)
            for parte in partes:
                # Fragmentar bloque si es necesario. Un párrafo muy largo también
                # Se divide en ventanas
                for texto in ventanas(parte.strip(), limite):
                    # Este es el fragmento o chunk
                    contenido = encabezado + texto

                    # Contar tokens del fragmento completo (encabezado + texto)
                    tokens = contar_tokens(contenido)

                    # Validar la cantidad de tokens del fragmento contra el menor entre
                    # esos dos, en ese caso MAX_TOKENS que es 95
                    if tokens > min(MAX_TOKENS, modelo.max_seq_length):
                        # Lanzar excepción en lugar de truncar texto en silencio
                        raise ValueError("Un fragmento supera el límite: ajuste el presupuesto.")

                    # Guardar fragmento y sus metadatos
                    registros.append({
                        **{ # Metadatos como clave: valor para el diccionario
                            k: documento[k]
                            for k in [
                                "document_id",
                                "source",
                                "title",
                                "version",
                                "source_hash"
                            ]
                        },
                        # Identificador único del fragmento.
                        # documento:versión:estrategia:número del fragmento
                        # ej. acceso:1.0-didactica:ventanas:0
                        "chunk_id": f"{documento['document_id']}:{documento['version']}:{estrategia}:{len(registros)}",
                        "section": seccion, # Título de la sección
                        "section_number": numero, # Número de la sección
                        "tokens": tokens, # Cantidad de tokens
                        "texto": contenido, # Fragmento completo (encabezado + texto)
                    })

    # Devolver todos los fragmentos generados
    return registros


# =====================================================================
# Comparación con el corpus guardado (necesidad de la aplicación)
# =====================================================================

def hay_cambios(cliente_db, corpus_id):
    """
    Indica si FUENTES o los parámetros de fragmentación difieren del corpus
    guardado en Supabase con ese corpus_id. No necesita el modelo.

    Compara la huella de cada documento original (source_hash), la versión y
    los parámetros. No compara la huella del índice: incluye los bytes de los
    vectores, que pueden variar entre máquinas aunque el texto sea el mismo.
    """
    if not corpus_id:
        return True

    datos = (
        cliente_db.table("clase08_fragmentos")
        .select("metadata,configuracion")
        .eq("corpus_id", corpus_id)
        .limit(501).execute().data
    )

    if not datos:
        return True

    locales = {(d["source"], d["source_hash"]) for d in leer_documentos()}
    guardados = {(r["metadata"].get("source"), r["metadata"].get("source_hash")) for r in datos}
    versiones = {r["metadata"].get("version") for r in datos}
    parametros = {
        (
            r["configuracion"].get("modelo"),
            r["configuracion"].get("estrategia"),
            r["configuracion"].get("max_tokens"),
            r["configuracion"].get("solapamiento")
        )
        for r in datos
    }

    return not (
        guardados == locales
        and versiones == {VERSION}
        and parametros == {(MODELO_EMBEDDINGS, ESTRATEGIA, MAX_TOKENS, SOLAPAMIENTO)}
    )


# =====================================================================
# Clases 7 y 8. Embeddings, validación, huella e identificador
# =====================================================================

def construir(revision=None):
    """
    Construye el índice del corpus y su identificador.

    Args:
        revision: revisión exacta del modelo. Si es None, se usa la revisión
            actual del modelo en Hugging Face, como en el prototipo.

    Returns:
        (corpus_id, registros, vectores, configuracion)
    """
    # Versión del modelo
    if revision is None:
        from huggingface_hub import model_info
        revision = model_info(MODELO_EMBEDDINGS).sha

    cargar_modelo(revision)

    registros = fragmentar(ESTRATEGIA, leer_documentos())

    # Calcular los embeddings del corpus.
    # Cada fila de la matriz representa un fragmento (384 dimensiones - columnas)
    vectores = modelo.encode(
        [r["texto"] for r in registros],
        normalize_embeddings=True, # Normalizar cada vector para longitud 1
        show_progress_bar=False
    )

    # Guardar configuración y parámetros
    configuracion = {
        "modelo": MODELO_EMBEDDINGS,
        "revision": revision,
        "estrategia": ESTRATEGIA,
        "max_tokens": MAX_TOKENS,
        "solapamiento": SOLAPAMIENTO,
        "normalizados": True,
        "similitud": "coseno",
        "max_seq_length": modelo.max_seq_length,
    }

    # Mismos bytes que registros.json, vectores.npy y configuracion.json del
    # ZIP de la clase 7, en el orden en que la clase 8 calculaba la huella
    vectores_npy = BytesIO()
    np.save(vectores_npy, vectores)
    datos = [
        json.dumps(registros, ensure_ascii=False, indent=2).encode("utf-8"),
        vectores_npy.getvalue(),
        json.dumps(configuracion, indent=2).encode("utf-8")
    ]

    validar_indice(registros, vectores, configuracion)

    huella = hashlib.sha256(b"".join(datos)).hexdigest()[:12]

    return f"{CORPUS_BASE}-{huella}", registros, vectores, configuracion


def validar_indice(registros, vectores, config):
    """
    Validaciones de la clase 8 (leer_indice y compatibilidad del modelo).
    """
    if config.get("modelo") != MODELO_EMBEDDINGS or not re.fullmatch(r"[0-9a-f]{40}", config.get("revision", "")):
        raise ValueError("Revisa el modelo y la revisión exacta guardados en el índice.")
    if config.get("normalizados") is not True or config.get("similitud") != "coseno":
        raise ValueError("Esta práctica utiliza vectores normalizados y similitud coseno.")
    if not isinstance(registros, list) or not 1 <= len(registros) <= 500:
        raise ValueError("Necesitamos entre 1 y 500 fragmentos.")
    if vectores.shape != (len(registros), 384) or not np.issubdtype(vectores.dtype, np.floating):
        raise ValueError("La matriz debe tener una fila por fragmento y 384 columnas numéricas.")
    if not np.isfinite(vectores).all() or not np.allclose(np.linalg.norm(vectores, axis=1), 1, atol=1e-3):
        raise ValueError("Hay vectores inválidos o sin normalizar.")

    # Validar metadatos en cada fragmento
    campos = ["chunk_id", "document_id", "texto", "source", "section", "version", "source_hash"]

    for registro in registros:
        # Si algún campo no es texto o está vacío, lanzar error
        if any(
            not isinstance(registro.get(campo), str)
            or not registro[campo].strip()
            for campo in campos
        ):
            raise ValueError("Un fragmento perdió su texto o sus metadatos requeridos.")

        # Lanzar error y no truncar de forma silenciosa
        if contar_tokens(registro["texto"]) > modelo.max_seq_length:
            raise ValueError("Un fragmento se truncaría: revisa su preparación.")

    if len({r["chunk_id"] for r in registros}) != len(registros):
        raise ValueError("Hay identificadores de fragmento repetidos.")


# =====================================================================
# Clase 8. Guardar en Supabase
# =====================================================================

def subir(cliente_db, usuario_id, corpus_id, registros, vectores, configuracion):
    """
    Guarda los fragmentos en clase08_fragmentos (clase 8, punto 5).
    Repetirlo actualiza las mismas filas en lugar de duplicarlas.
    """
    # Construir lista de filas a insertar en Supabase
    filas = [{
        "owner_id": usuario_id,
        "corpus_id": corpus_id,
        "chunk_id": r["chunk_id"],
        "content": r["texto"],
        "metadata": {
            k: v for k, v in r.items()
            if k not in ["texto", "chunk_id"]
        },
        "configuracion": configuracion,
        "embedding": vectores[i].tolist(), # Pasar el vector de numpy a lista
    } for i, r in enumerate(registros)]

    # Insertar o actualizar por lotes de 50
    for inicio in range(0, len(filas), 50):
        cliente_db.table("clase08_fragmentos").upsert(
            filas[inicio:inicio + 50], on_conflict="owner_id,corpus_id,chunk_id"
        ).execute()

    # Consultar por usuario y corpus. Una fila para revisar y conteo
    lectura = (
        cliente_db.table("clase08_fragmentos")
        .select("chunk_id", count="exact")
        .eq("owner_id", usuario_id)
        .eq("corpus_id", corpus_id)
        .limit(1)
        .execute()
    )

    # Validar número de filas. Filas en supabase = fragmentos originales
    if lectura.count != len(registros):
        raise ValueError("El número de filas no coincide con el índice.")


# =====================================================================
# Compartir la versión y actualizar app/.env (necesidad de la aplicación)
# =====================================================================

def compartir(cliente_db, usuario_id, corpus_id):
    """
    Registra el corpus en corpus_compartidos para que lo lean todos los
    usuarios autenticados. Requiere que la cuenta esté en
    administradores_corpus (migración 003).
    """
    existente = (
        cliente_db.table("corpus_compartidos")
        .select("corpus_id,owner_id")
        .eq("corpus_id", corpus_id)
        .execute().data
    )

    if existente:
        if existente[0]["owner_id"] != usuario_id:
            raise ValueError("Ese corpus ya está compartido por otra cuenta.")
        return

    cliente_db.table("corpus_compartidos").insert({"corpus_id": corpus_id}).execute()


def actualizar_env(ruta_env, corpus_id, revision):
    """
    Escribe CORPUS_ID y EMBEDDINGS_REVISION en app/.env sin modificar las demás
    líneas, y los actualiza en el proceso actual.
    """
    from dotenv import set_key

    for clave, valor in [("CORPUS_ID", corpus_id), ("EMBEDDINGS_REVISION", revision)]:
        set_key(str(ruta_env), clave, valor, quote_mode="never")
        os.environ[clave] = valor


def sincronizar(cliente_db, usuario_id, corpus_id_actual, ruta_env):
    """
    Sin cambios en FUENTES ni en los parámetros, no modifica nada. Con cambios,
    construye una versión nueva, la guarda, la comparte y actualiza app/.env.
    Las versiones anteriores no se borran.

    Returns:
        {"cambios": bool, "corpus_id": str}
    """
    if not hay_cambios(cliente_db, corpus_id_actual):
        return {"cambios": False, "corpus_id": corpus_id_actual}

    corpus_id, registros, vectores, configuracion = construir()
    subir(cliente_db, usuario_id, corpus_id, registros, vectores, configuracion)

    try:
        compartir(cliente_db, usuario_id, corpus_id)
    except Exception as error:
        raise RuntimeError(
            f"La versión {corpus_id} del corpus se guardó, pero no se pudo compartir. "
            "Revisa que la cuenta de CORPUS_EMAIL esté en administradores_corpus "
            "(migración 003). app/.env no se modificó."
        ) from error

    actualizar_env(ruta_env, corpus_id, configuracion["revision"])

    return {"cambios": True, "corpus_id": corpus_id}
