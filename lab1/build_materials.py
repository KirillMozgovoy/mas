"""Build report and offline trace viewer from actual simulation runs."""
import html
import json
import re
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak, Flowable)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
RESULTS = {name: json.loads((ROOT / 'demo' / f'{name}.json').read_text())
           for name in ('normal', 'overload', 'capacity')}
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DV', str(FONT_DIR / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DV-Bold', str(FONT_DIR / 'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DV', normal='DV', bold='DV-Bold', italic='DV', boldItalic='DV-Bold')
NAVY, BLUE, LIGHT = colors.HexColor('#142C45'), colors.HexColor('#206EAC'), colors.HexColor('#EDF4FA')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TextRU', fontName='DV', fontSize=10, leading=15,
                         textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name='TitleRU', fontName='DV-Bold', fontSize=23, leading=29,
                         textColor=NAVY, spaceAfter=14))
styles.add(ParagraphStyle(name='H1RU', fontName='DV-Bold', fontSize=16, leading=21,
                         textColor=NAVY, spaceAfter=13))
styles.add(ParagraphStyle(name='H2RU', fontName='DV-Bold', fontSize=11, leading=16,
                         textColor=BLUE, spaceBefore=5, spaceAfter=7))
styles.add(ParagraphStyle(name='SmallRU', fontName='DV', fontSize=8.3, leading=12,
                         textColor=NAVY, spaceAfter=5))
story, markdown = [], []


def text(s, style='TextRU'):
    story.append(Paragraph(s, styles[style]))
    markdown.append(re.sub('<[^>]+>', '', s))


def heading(s):
    story.append(Paragraph(s, styles['H2RU']))
    markdown.append('## ' + s)


def page(title):
    if story:
        story.append(PageBreak())
    story.append(Paragraph(title, styles['H1RU']))
    markdown.append('# ' + title)


def table(headers, rows, widths):
    data = [[Paragraph(html.escape(str(v)), styles['SmallRU']) for v in row]
            for row in [headers] + rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,0), .8, BLUE),
        ('LINEBELOW', (0,1), (-1,-1), .3, colors.HexColor('#D9E3EC')),
        ('LEFTPADDING',(0,0),(-1,-1),7), ('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7), ('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    story.extend([t, Spacer(1, 10)])
    markdown.append('| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---']*len(headers)) + ' |')
    markdown.extend('| ' + ' | '.join(map(str,row)) + ' |' for row in rows)


class Diagram(Flowable):
    def __init__(self, mode):
        Flowable.__init__(self)
        self.mode, self.width, self.height = mode, 499, 195

    def draw(self):
        c = self.canv
        def box(x,y,w,h,lines):
            c.setFillColor(LIGHT); c.setStrokeColor(BLUE)
            c.roundRect(x,y,w,h,6,fill=1,stroke=1)
            c.setFillColor(NAVY)
            for i,s in enumerate(lines):
                c.setFont('DV-Bold' if i==0 else 'DV',9 if i==0 else 8)
                c.drawCentredString(x+w/2,y+h-18-i*14,s)
        def arrow(x1,y1,x2,y2,both=False):
            import math
            c.setStrokeColor(BLUE); c.setLineWidth(1)
            c.line(x1,y1,x2,y2)
            def tip(x,y,a):
                c.line(x,y,x-6*math.cos(a-.4),y-6*math.sin(a-.4))
                c.line(x,y,x-6*math.cos(a+.4),y-6*math.sin(a+.4))
            a=math.atan2(y2-y1,x2-x1); tip(x2,y2,a)
            if both: tip(x1,y1,a+math.pi)
        if self.mode=='roles':
            box(160,137,180,50,['Роль: диспетчер','1 агент · назначение заказов'])
            box(0,8,145,64,['Роль: источник','1 агент','создание заявок'])
            box(175,8,145,64,['Роль: курьер','3 агента','проверка и исполнение'])
            arrow(72,72,185,137); arrow(250,137,247,72,True)
            c.setFillColor(NAVY); c.setFont('DV',8)
            c.drawString(8,105,'поставляет задания'); c.drawString(300,105,'координирует')
        else:
            box(0,134,120,48,['source','генератор заказов'])
            box(179,134,143,48,['dispatcher','центральный узел'])
            for x, cid in [(0,'courier_1'),(177,'courier_2'),(354,'courier_3')]:
                box(x,3,144,48,[cid,'исполнитель доставки'])
                arrow(250,134,x+72,51,True)
            arrow(120,158,179,158)
            c.setFillColor(NAVY); c.setFont('DV',7)
            c.drawString(124,168,'REQUEST')
            c.drawCentredString(250,91,'ASSIGN →   ← ACCEPT / REJECT / PICKED_UP / DELIVERED / STATUS')


page('Лабораторная работа №1')
text('Спецификация и архитектурное проектирование многоагентной системы', 'TitleRU')
text('Курс «Теория многоагентных систем» · 12 ноября 2026 года', 'SmallRU')
text('<b>Выполнил:</b> Мозговой Кирилл Сергеевич<br/><b>Группа:</b> Б24-517')
heading('Тема и цель')
text('Распределение заказов между автономными курьерами. Цель работы — сформулировать задачу, определить агентов, их знания, состояния и полномочия, спроектировать взаимодействие и обосновать архитектуру, пригодную для исследований в ЛР2–ЛР4.')
heading('1. Прикладная задача')
text('Служба доставки получает заказы с координатами получения и доставки, массой и желательным сроком выполнения. Курьеры различаются местоположением, скоростью и грузоподъёмностью. Система должна назначать выполнимые заказы, отслеживать исполнение и сохранять журнал обмена сообщениями.')
text('Курьер представлен агентом, поскольку располагает локальным состоянием и собственным правилом принятия задания. Назначение диспетчера является предложением: занятый курьер или курьер с недостаточной грузоподъёмностью отклоняет его. Это позволяет явно отделить координацию от исполнения.')
heading('Постановка и критерии')
text('Вход: множество заказов O и множество курьеров C. Заказ o = (id, r, p, d, w, D): идентификатор, время поступления, точка получения, точка доставки, масса и дедлайн. Профиль курьера c = (id, x₀, K, v): начальная позиция, грузоподъёмность и скорость.')
text('Выход: назначение исполнителей, состояния заказов, времена доставки и трасса сообщений. Обязательные ограничения: один активный заказ на курьера; масса заказа не больше грузоподъёмности; один исполнитель на заказ; доставка только после получения. Опоздание допускается и учитывается отдельно.')
heading('Допущения модели')
text('Город — целочисленная сетка; расстояние — манхэттенское. Время дискретное, погрузка и выгрузка мгновенные. Курьеры движутся сначала по оси x, затем по y. Частичное обслуживание и передача груза между курьерами не предусмотрены. Все агенты работают в одном процессе через надёжную FIFO-шину; задержки и потери связи в ЛР1 отсутствуют.')

page('2. Формальное описание агентов')
text('Система задаётся как M = (A, O, S, Act, Msg, T), где A = {source, dispatcher, courier_1, courier_2, courier_3}; S — совокупность локальных состояний; Act — действия агентов; Msg — типизированные сообщения; T — дискретный шаг моделирования.')
heading('Источник заказов — source')
text('<b>Цель:</b> передать предусмотренные сценарием заявки в момент r. <b>Знания:</b> список заказов и времена их появления. <b>Состояние:</b> текущий момент симуляции; перечень задан статически. <b>Действие:</b> отправить REQUEST диспетчеру. <b>Полномочия:</b> создавать заказы, но не выбирать исполнителя и не менять их статус. <b>Средства:</b> сценарий и исходящий канал source → dispatcher.')
heading('Диспетчер — dispatcher')
text('<b>Цель:</b> назначать ожидающие заказы доступным исполнителям, уменьшая оценку времени маршрута. <b>Знания:</b> реестр заказов, статические профили курьеров, последние STATUS, ожидаемые ответы, подтверждённые назначения и времена доставки. <b>Состояние:</b> waiting / offered / assigned / in_transit / delivered для каждого заказа. <b>Действия:</b> выбрать кандидата, зарезервировать его, отправить ASSIGN, обработать ответ и обновить реестр.')
text('<b>Полномочия:</b> предлагать заказы и вести общий реестр. Диспетчер не меняет напрямую позицию, груз или состояние курьера. <b>Средства:</b> очередь заказов, функция оценки маршрута и каналы dispatcher ↔ courier_i. Сведения об исполнении поступают только из сообщений.')
heading('Курьеры — courier_i')
text('<b>Локальная цель:</b> выполнить принятое задание без превышения собственной грузоподъёмности и без двух одновременных заказов. В ЛР1 агенты кооперативны, денежная полезность не вводится. <b>Знания:</b> текущая позиция, скорость, грузоподъёмность, принятый заказ и множество ранее принятых идентификаторов. Курьер не знает очереди остальных агентов.')
text('<b>Состояния:</b> idle, to_pickup, to_destination. <b>Действия:</b> проверить предложение, принять или отклонить его, переместиться, получить и доставить заказ, сообщить состояние. <b>Полномочия:</b> управлять только собственным исполнением. <b>Средства:</b> локальный маршрут и канал courier_i ↔ dispatcher.')
table(['Агент', 'Стартовая позиция', 'Грузоподъёмность', 'Скорость'],[
    ['courier_1','(0, 0)','3 ед. массы','1 клетка/такт'],
    ['courier_2','(8, 0)','6 ед. массы','1 клетка/такт'],
    ['courier_3','(4, 8)','4 ед. массы','2 клетки/такт']], [112,126,132,129])

page('3. Архитектура и коммуникации')
heading('Диаграмма ролей')
story.append(Diagram('roles'))
markdown.append('Диаграмма ролей: источник → диспетчер ↔ курьеры. Роли: создание заявок; назначение; проверка и исполнение.')
heading('Граф коммуникаций')
story.append(Diagram('communication'))
markdown.append('Граф: source → dispatcher; dispatcher ↔ courier_1; dispatcher ↔ courier_2; dispatcher ↔ courier_3. Прямых каналов между курьерами нет.')
heading('Обоснование выбора')
text('Выбрана иерархическая МАС с централизованной координацией и автономными исполнителями. Для небольшой службы это даёт простой реестр назначений и позволяет исключить конкурирующие назначения резервированием. Различие скоростей и грузоподъёмностей учитывается явно; решения исполнителей остаются локальными.')
text('Цена решения — единая точка отказа и концентрация сообщений у диспетчера. Координация пока не распределённая; отказ центрального узла, устаревшие сведения и недостоверные ответы требуют отдельных механизмов. Эти ограничения задают предмет следующих работ.')
text('Шина Bus — инфраструктура передачи, не отдельный агент: у неё нет цели выбора исполнителя. Классы агентов обмениваются сообщениями и не вызывают методы изменения состояния друг друга. Планировщик симуляции только упорядочивает обработку и движение.')

page('4. Протокол и правила взаимодействия')
table(['Сообщение', 'Направление', 'Содержание и эффект'],[
 ['REQUEST','source → dispatcher','Все поля заказа; новый id регистрируется как waiting.'],
 ['ASSIGN','dispatcher → courier','Все поля заказа; диспетчер ставит offered и резервирует кандидата.'],
 ['ACCEPT','courier → dispatcher','id заказа; при совпадении ожидаемого отправителя фиксируются assigned и исполнитель.'],
 ['REJECT','courier → dispatcher','id, позиция, idle; снимается ожидание ответа, заказ возвращается в waiting.'],
 ['PICKED_UP','courier → dispatcher','id; переход assigned → in_transit от подтверждённого исполнителя.'],
 ['DELIVERED','courier → dispatcher','id; переход in_transit → delivered и фиксация времени.'],
 ['STATUS','courier → dispatcher','Позиция и idle после такта активного курьера; обновление знаний диспетчера.']], [96,120,283])
heading('Выбор исполнителя')
text('Заказы рассматриваются по (время поступления, id). Кандидаты — свободные курьеры с K ≥ w. Для каждого вычисляется оценка τ = (|x − p|₁ + |p − d|₁) / v. Выбирается минимум τ, при равенстве — лексикографически меньший id. Это локальная эвристика без доказанной глобальной оптимальности; дедлайн в приоритезацию не входит.')
heading('Переходы и защита ограничений')
text('Заказ: waiting → offered → assigned → in_transit → delivered; при отказе offered → waiting. Курьер: idle → to_pickup → to_destination → idle. Принять можно только новый id при idle и w ≤ K. Резервирование кандидата до отправки ASSIGN не позволяет предложить ему второй заказ в том же цикле. Повтор ASSIGN для уже принятого id не запускает исполнение повторно.')
text('Ответ ACCEPT/REJECT обрабатывается только от ожидаемого кандидата. PICKED_UP и DELIVERED учитываются от закреплённого исполнителя в допустимом состоянии. Это проверки логической согласованности, а не аутентификация: криптографической проверки отправителя нет.')
text('При отсутствии кандидата заказ остаётся waiting. В надёжной синхронной модели ответ поступает в том же цикле обработки шины; таймаут назначения не реализован. В моделях с потерями сообщений необходимо добавить таймаут, повтор и идентификатор попытки.')

page('5. Прототип и проверка архитектуры')
heading('Реализация')
text('Прототип написан на Python 3.10+ со стандартной библиотекой. В src/simulation.py явно реализованы Source, Dispatcher, Courier и Bus. Шаг: поступление заявок → обработка шины → назначение → обработка ответов → движение → обработка событий. Доставка фиксируется в конце такта; даже нулевой маршрут завершается не раньше конца такта назначения.')
text('В одном такте курьер проходит не больше v клеток, включая оба участка маршрута; оставшийся после получения бюджет движения может использоваться для доставки. Заказ, завершённый в конце такта, освобождает курьера для назначения в следующем такте.')
heading('Сценарии и фактические результаты')
text('Проверены три детерминированных сценария при политике nearest и пределе 120 тактов. Normal: 6 заказов с поступлением в такты 0–4. Overload: 18 заказов в такт 0 с дедлайном 10. Capacity: normal плюс заказ HEAVY массой 9 при максимальной грузоподъёмности 6. Полные входные данные и трассы вынесены в приложения.')
rows=[]
for key,label in [('normal','Normal'),('overload','Overload'),('capacity','Capacity')]:
    r=RESULTS[key]; m=r['metrics']
    rows.append([label,f"{m['delivered']}/{m['total']}",r['elapsed'],m['late'],m['mean_delivery_time'],m['messages'],m['travel']])
table(['Сценарий','Доставлено','Такты','Поздно','Ср. время','Сообщ.','Путь'],rows,[82,77,59,56,79,71,75])
text('Среднее время = среднее (время доставки − время поступления) только по доставленным заказам. «Поздно» — число доставок строго после дедлайна. «Сообщ.» включает STATUS; «Путь» — сумма пройденных клеток. «Такты» — длительность запуска, а не средняя задержка.', 'SmallRU')
heading('Интерпретация')
text('В обычном режиме все 6 заказов доставлены за 12 тактов без опозданий. При перегрузке все 18 доставлены, но 16 опоздали: отсутствие учёта дедлайнов и ограниченная производительность существенны. В сценарии capacity шесть обычных заказов завершены, HEAVY остаётся waiting до предела. Система сохраняет ограничение по массе, но не умеет эскалировать невыполнимую заявку.')
heading('Проверки корректности')
text('Пять тестов unittest завершились успешно. Проверяются завершение выполнимых сценариев для двух политик; единственность принятия и ограничение массы; изоляция невыполнимого заказа; отказ занятого/перегруженного агента и повтор ASSIGN; будущая заявка с нулевым маршрутом; детерминизм и причинный порядок REQUEST → ASSIGN → ACCEPT → PICKED_UP → DELIVERED. Это функциональные проверки прототипа, не исследование надёжности ЛР4.')

page('6. Развитие системы и выводы')
heading('Пригодность для последующих лабораторных')
table(['Работа','Планируемое исследование'],[
 ['ЛР2. Распределение','Сравнить nearest и round_robin на одинаковых входах, затем при необходимости реализовать контрактную сеть. Менять интенсивность поступления и состав курьеров; измерять задержку, опоздания, сообщения и путь. Две первые политики уже переключаются в прототипе; сравнительное исследование в ЛР1 не проводилось.'],
 ['ЛР3. Конфликты','Ввести ограниченное число мест погрузки в одном депо. Курьеры конкурируют за интервалы; сравнить обслуживание без переговоров и с запросом временного слота, приоритетом по дедлайну и ростом приоритета ожидания. Измерять задержку и справедливость доступа. Пока не реализовано.'],
 ['ЛР4. Надёжность','Моделировать отказ курьера, потерю ответа, устаревший STATUS и неверное сообщение о завершении. Добавить таймауты, идентификаторы попыток, контроль переходов и переназначение; сравнить трассы и долю завершённых заказов. Пока не реализовано.']], [119,380])
heading('Ограничения результата')
text('Рассматривается логическая модель, а не промышленная служба доставки: нет дорог с препятствиями, реального времени, сетевых процессов, аутентификации и оплаты. Автономия курьеров ограничена принятием и исполнением заказа; переговоры об условиях не реализованы. Реестр seen растёт без очистки, что приемлемо для небольших сценариев, но требует политики хранения при длительной работе.')
heading('Вывод')
text('Сформулирована прикладная задача и спроектирована МАС из пяти агентов трёх ролей. Определены знания, цели, состояния, действия, полномочия и каналы; построены диаграмма ролей и граф коммуникаций. Центральная координация обеспечивает обозримый протокол назначения, а локальные проверки курьеров сохраняют ограничения исполнения. Работоспособность архитектуры подтверждена прототипом и воспроизводимыми запусками. Структура допускает расширение для ЛР2–ЛР4.')
heading('Источник требований и приложения')
text('Источник: «Рекомендации по выполнению лабораторных работ по курсу “Теория многоагентных систем”», файл «Лабораторные-МАС.pdf», с. 1–2. Требования к ЛР1 — с. 2; общие требования к реализации и отчёту — с. 1.', 'SmallRU')
text('Исходный код и демонстрационные материалы размещены в репозитории GitHub:<br/><link href="https://github.com/KirillMozgovoy/mas/tree/main/lab1" color="#206EAC">https://github.com/KirillMozgovoy/mas/tree/main/lab1</link><br/>Состав: src/simulation.py, tests/test_simulation.py, demo/index.html и demo/*.json. Инструкции запуска — README.md. В настоящий отчёт исходный код и демонстрационные трассы не включены.', 'SmallRU')


def footer(c, doc):
    c.setStrokeColor(colors.HexColor('#CBD8E4')); c.line(48,43,547,43)
    c.setFont('DV',8); c.setFillColor(NAVY)
    c.drawString(48,29,'МАС · ЛР1 · Распределение заказов между курьерами')
    c.drawRightString(547,29,str(doc.page))


SimpleDocTemplate(str(ROOT/'report.pdf'), pagesize=(595.28,841.89),
    leftMargin=48,rightMargin=48,topMargin=43,bottomMargin=60,
    title='МАС — лабораторная работа №1', author='Мозговой Кирилл Сергеевич',
    subject='Спецификация и архитектурное проектирование МАС').build(story,onFirstPage=footer,onLaterPages=footer)
(ROOT/'report.md').write_text('\n\n'.join(markdown)+'\n',encoding='utf-8')

VIEWER = '''<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>МАС · просмотр запусков</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#eef3f8;color:#142c45;font:15px/1.5 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:36px 24px}h1{font-size:30px;margin:8px 0}h2{font-size:19px}p{color:#476079}
.tag{font-size:12px;letter-spacing:2px;color:#206eac;font-weight:700}.row{display:flex;gap:16px;flex-wrap:wrap}
.card{background:white;border:1px solid #d8e3ed;border-radius:12px;padding:18px;margin:16px 0}
.metric{flex:1;min-width:140px}.metric strong{display:block;font-size:28px}select{padding:10px;font:inherit;border:1px solid #a9bfd1;border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:9px;border-bottom:1px solid #e3eaf1;vertical-align:top}th{color:#476079}
.scroll{max-height:420px;overflow:auto}code{font-size:12px;white-space:pre-wrap}svg{display:block;max-width:100%;margin:auto}small{color:#476079}
</style><main><div class="tag">ТЕОРИЯ МНОГОАГЕНТНЫХ СИСТЕМ · ЛР1</div>
<h1>Курьеры и заказы</h1><p>Просмотр сохранённых детерминированных запусков. Python запускается отдельно по README.</p>
<label>Сценарий: <select id="scenario"><option value="normal">Обычная нагрузка</option><option value="overload">Перегрузка</option><option value="capacity">Невыполнимый заказ</option></select></label>
<div id="description"></div><div class="row" id="metrics"></div>
<section class="card"><h2>Состояния заказов после запуска</h2><div style="overflow:auto"><table id="orders"></table></div></section>
<div class="row"><section class="card" style="flex:1;min-width:320px"><h2>Курьеры после запуска</h2><div id="couriers"></div></section>
<section class="card" style="flex:1;min-width:320px"><h2>Граф коммуникаций</h2><svg viewBox="0 0 420 230" aria-label="Источник передаёт заказы диспетчеру, диспетчер обменивается сообщениями с тремя курьерами"><defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="#206eac"/></marker></defs><g stroke="#206eac" marker-end="url(#a)"><path d="M110 45H165"/><path d="M230 75L75 162" marker-start="url(#a)"/><path d="M230 75V162" marker-start="url(#a)"/><path d="M230 75L360 162" marker-start="url(#a)"/></g><g fill="#edf4fa" stroke="#206eac"><rect x="5" y="18" width="105" height="55" rx="7"/><rect x="170" y="18" width="120" height="55" rx="7"/><rect x="8" y="165" width="127" height="45" rx="7"/><rect x="165" y="165" width="127" height="45" rx="7"/><rect x="310" y="165" width="108" height="45" rx="7"/></g><g fill="#142c45" font-family="sans-serif" font-size="13" text-anchor="middle"><text x="57" y="50">source</text><text x="230" y="50">dispatcher</text><text x="72" y="192">courier_1</text><text x="230" y="192">courier_2</text><text x="364" y="192">courier_3</text></g></svg></section></div>
<section class="card"><h2>Журнал сообщений <small id="count"></small></h2><label>Тип: <select id="filter"><option value="">Все сообщения</option></select></label><div class="scroll"><table id="trace"></table></div></section>
<small>Один такт — единица условного времени. Среднее считается по доставленным заказам; STATUS входит в число сообщений. Новые JSON автоматически в HTML не подгружаются: для обновления встроенных запусков выполните build_materials.py.</small></main>
<script>const data=__DATA__;
const names={normal:'6 заказов, поступающих в такты 0–4; политика nearest.',overload:'18 заказов в такт 0, дедлайн каждого — такт 10; политика nearest.',capacity:'6 обычных заказов и HEAVY массой 9 при максимальной грузоподъёмности 6; горизонт — 120 тактов.'};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const coord=p=>'('+p.join(', ')+')';
const state={delivered:'Доставлен',waiting:'В очереди',offered:'Предложен',assigned:'Назначен',in_transit:'В пути',not_released:'Не поступил'};
const head=a=>'<tr>'+a.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr>';
const row=a=>'<tr>'+a.map(x=>'<td>'+esc(x)+'</td>').join('')+'</tr>';
function render(){let r=data[document.querySelector('#scenario').value],m=r.metrics;
document.querySelector('#description').innerHTML='<p>'+names[r.scenario]+'</p>';
document.querySelector('#metrics').innerHTML=[['Доставлено',m.delivered+'/'+m.total],['Длительность',r.elapsed+' тактов'],['Среднее время',m.mean_delivery_time],['Опозданий',m.late],['Сообщений',m.messages],['Путь',m.travel]].map(([a,b])=>'<div class="card metric">'+a+'<strong>'+b+'</strong></div>').join('');
document.querySelector('#orders').innerHTML=head(['Заказ','Поступил','Получение → доставка','Масса','Дедлайн','Курьер','Завершён','Состояние'])+r.orders.map(o=>row([o.id,o.release,coord(o.pickup)+' → '+coord(o.destination),o.weight,o.deadline,r.assignment[o.id]||'—',r.completed[o.id]??'—',state[r.states[o.id]]||r.states[o.id]])).join('');
document.querySelector('#couriers').innerHTML='<table>'+head(['Курьер','Позиция','Состояние','Путь'])+r.couriers.map(c=>row([c.id,coord(c.position),c.state,c.travel])).join('')+'</table>';
let filter=document.querySelector('#filter');const selected=filter.value;
filter.innerHTML='<option value="">Все сообщения</option>'+[...new Set(r.trace.map(m=>m.kind))].map(k=>'<option>'+k+'</option>').join('');filter.value=selected;
renderTrace();}
function renderTrace(){let r=data[document.querySelector('#scenario').value],f=document.querySelector('#filter').value,a=r.trace.filter(m=>!f||m.kind===f);
document.querySelector('#count').textContent='('+a.length+' из '+r.trace.length+')';
document.querySelector('#trace').innerHTML=head(['Такт','Отправитель','Получатель','Тип','Данные'])+a.map(m=>row([m.time,m.sender,m.receiver,m.kind,JSON.stringify(m.payload)])).join('');}
document.querySelector('#scenario').onchange=render;document.querySelector('#filter').onchange=renderTrace;render();
</script></html>'''
(ROOT/'demo/index.html').write_text(VIEWER.replace('__DATA__',json.dumps(RESULTS,ensure_ascii=False)),encoding='utf-8')
print('Built report.pdf, report.md, demo/index.html')
