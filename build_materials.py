"""Rebuild reports and offline demos after running both simulations. Requires reportlab."""
from pathlib import Path
import json, statistics, html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parent
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
import os
FONT=Path(os.environ.get('REPORT_FONT',str(FONT)))
pdfmetrics.registerFont(TTFont('Body',str(FONT)))
styles=getSampleStyleSheet()
for key in ('Normal','Title','Heading1','Heading2'):styles[key].fontName='Body'
styles['Normal'].fontSize=9.5;styles['Normal'].leading=13
styles['Title'].fontSize=20;styles['Title'].leading=26
styles['Heading1'].fontSize=15;styles['Heading1'].leading=20
styles['Heading2'].fontSize=12;styles['Heading2'].leading=17
small=ParagraphStyle('small',parent=styles['Normal'],fontSize=8,leading=11)
def footer(canvas,doc):
 canvas.setFont('Body',8);canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawString(42,25,'МАС • Мозговой Кирилл • Б24-517');canvas.drawRightString(553,25,str(doc.page))
def make(n,title,sections,headers,rows):
 root=ROOT/f'lab{n}';story=[];md=[f'# Лабораторная работа {n}. {title}','Мозговой Кирилл Сергеевич, Б24-517. МИФИ, 2026.']
 story += [Paragraph(f'Лабораторная работа {n}',styles['Title']),Paragraph(title,styles['Heading1']),Paragraph(md[1],styles['Normal']),Spacer(1,16)]
 for heading,paras in sections:
  if heading.startswith('4.') or (n==4 and heading.startswith('5.')):story.append(PageBreak())
  story.append(Paragraph(heading,styles['Heading2']));md.append('## '+heading)
  for p in paras:
   if p=='TABLE':
    data=[[Paragraph(html.escape(str(c)),small) for c in row] for row in [headers]+rows]
    t=Table(data,repeatRows=1,hAlign='LEFT',colWidths=[511/len(headers)]*len(headers));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd5e1')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t)
    md+=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows]
   else:story.append(Paragraph(html.escape(p),styles['Normal']));story.append(Spacer(1,5));md.append(p)
  story.append(Spacer(1,5))
 story += [Paragraph('Материалы',styles['Heading2']),Paragraph(f'<link href="https://github.com/KirillMozgovoy/mas/tree/main/lab{n}">github.com/KirillMozgovoy/mas/tree/main/lab{n}</link>',styles['Normal'])]
 md.append(f'Материалы: https://github.com/KirillMozgovoy/mas/tree/main/lab{n}')
 (root/'report.md').write_text('\n\n'.join(md),encoding='utf-8')
 SimpleDocTemplate(str(root/'report.pdf'),pagesize=(595,842),leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=45,title=f'МАС. ЛР{n}. {title}',author='Мозговой Кирилл Сергеевич').build(story,onFirstPage=footer,onLaterPages=footer)
 (root/'README.md').write_text(f'''# ЛР{n}. {title}

Мозговой Кирилл Сергеевич, Б24-517.

[Отчёт PDF](report.pdf) · [Отчёт текстом](report.md) · [Результаты](results.json)

## Запуск

Нужен Python 3.10 или новее. Симуляция использует только стандартную библиотеку.

```bash
cd lab{n}
python simulation.py
python -m unittest -v
```

Откройте `demo/index.html` в браузере после скачивания репозитория. Это просмотр сохранённых трасс seed=0, а не отдельная симуляция. Можно выбрать сценарий и шаг времени, изучить события и итоговые метрики. Сервер не нужен.

`results.json` содержит все прогоны, `traces.json` - полные трассы для seed=0. Для обновления демонстраций и PDF после экспериментов выполните из корня репозитория `python build_materials.py` (нужен `reportlab`; путь к шрифту DejaVu Sans можно передать через переменную `REPORT_FONT`).

Модель, параметры, определения метрик и ограничения описаны в отчёте. Это отдельная подмодель курьерской МАС, без расчёта маршрутов.
''',encoding='utf-8')
 traces=json.loads((root/'traces.json').read_text());(root/'demo').mkdir(exist_ok=True)
 template='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>МАС - ЛРNUM</title><style>body{font:16px system-ui;background:#101827;color:#edf2f7;margin:32px auto;max-width:1100px;padding:0 20px}h1{font-size:30px}select,input{padding:10px;font:inherit}section{background:#1e293b;padding:20px;border-radius:12px;margin:20px 0}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #475569}pre{white-space:pre-wrap}.muted{color:#b4c4d7}input{width:70%}</style><h1>ЛРNUM · TITLE</h1><p class="muted">Записанные эксперименты, seed=0. Результаты рассчитаны Python-моделью. Шаг времени показывает накопленный журнал, итоговые метрики относятся ко всему прогону.</p><label>Сценарий <select id="scenario"></select></label><section><label>Время <input id="time" type="range" min="0"><output id="tick"></output></label><p id="count"></p><div style="max-height:470px;overflow:auto"><table><thead><tr><th>Время</th><th>Отправитель</th><th>Получатель</th><th>Событие</th><th>Заказ</th></tr></thead><tbody id="events"></tbody></table></div></section><section><h2>Итоги прогона</h2><pre id="metrics"></pre></section><p>REQUEST - запрос места; GRANT - выдача места; RELEASE - освобождение; CONFLICT - конфликт. ASSIGN - назначение; DONE - подтверждение; PHYSICAL_DELIVERY - факт выполнения; DROP - потеря; REVOKE - отзыв; VERIFY_RECEIPT - проверка квитанции.</p><script>const runs=DATA;const sel=document.getElementById('scenario'), slider=document.getElementById('time');runs.forEach((r,i)=>{let o=document.createElement('option');o.value=i;o.textContent=r.mode?`${r.mode}, мест: ${r.bays}`:`${r.scenario}, защита: ${r.protected?'да':'нет'}`;sel.append(o)});function draw(){const r=runs[sel.value];document.getElementById('tick').textContent=slider.value;const events=r.trace.filter(e=>e.time<=+slider.value);document.getElementById('count').textContent=`Событий к выбранному моменту: ${events.length}`;document.getElementById('events').replaceChildren(...events.map(e=>{let tr=document.createElement('tr');[e.time,e.sender,e.receiver,e.kind,e.job].forEach(x=>{let td=document.createElement('td');td.textContent=x;tr.append(td)});return tr}));const metrics=Object.fromEntries(Object.entries(r).filter(([k])=>!['trace','jobs','completed_ids','durations'].includes(k)));document.getElementById('metrics').textContent=JSON.stringify(metrics,null,2)}function change(){slider.max=Math.max(...runs[sel.value].trace.map(e=>e.time));slider.value=slider.max;draw()}sel.onchange=change;slider.oninput=draw;change();</script></html>'''
 (root/'demo/index.html').write_text(template.replace('NUM',str(n)).replace('TITLE',html.escape(title)).replace('DATA',json.dumps(traces,ensure_ascii=False)),encoding='utf-8')
def avg(rs,k):
 a=[r[k] for r in rs if r[k] is not None];return (f'{statistics.mean(a):.3f}' if k=='fairness' else f'{statistics.mean(a):.2f}') if a else '-'
r3=json.loads((ROOT/'lab3/results.json').read_text());rows3=[]
for b in (1,2):
 for m in ('uncoordinated','fifo','priority'):
  rs=[r for r in r3 if r['bays']==b and r['mode']==m];rows3.append([str(b),m,avg(rs,'completed'),avg(rs,'late'),avg(rs,'mean_wait'),avg(rs,'fairness')])
make(3,'Разрешение конфликтов при дефиците ресурсов',[
('1. Цель и связь с проектом',['Исследовать конфликт курьеров за ограниченное число погрузочных мест и сравнить механизмы его разрешения. В ЛР1 задана курьерская МАС, в ЛР2 исследовано назначение заказов. Здесь рассматривается следующий этап: доступ назначенных курьеров к общему ресурсу склада. Модель автономна; исходный симулятор ЛР2 не изменяется.']),
('2. Агенты, интересы и среда',['Шесть курьеров стремятся обслужить свои заказы раньше срока. Склад предоставляет одно или два места. Одновременно курьер выполняет не более одного заказа. Среда хранит время, занятые места и момент окончания погрузки. Арбитр склада принимает заявки и выдаёт разрешения. Конфликт возникает, когда число претендентов превышает свободную вместимость.','60 заказов поступают пакетами по 6 каждые 3 такта; у каждого курьера 10 заказов. Длительность обслуживания равномерно выбирается из целых 2..5, срок равен времени поступления плюс случайное целое 8..25. Курьер предлагает свой самый ранний ожидающий заказ. Сроки мягкие: просроченные заявки не удаляются.']),
('3. Механизмы разрешения',['Без согласования: все претенденты одновременно пытаются занять ресурс. Если свободных мест недостаточно для всех, попытки отклоняются, а на следующем такте повторяются синхронно. Это специально выбранный неблагоприятный протокол без случайной задержки: он допускает livelock. Такой исход нельзя переносить на любые децентрализованные протоколы.','FIFO: арбитр сортирует заявки по времени поступления, затем по номеру заказа и выдаёт разрешения на свободные места. Приоритет: ожидающие не менее 20 тактов идут первыми в порядке поступления; остальные сортируются по сроку, затем номеру. Старение ограничивает вытеснение давно ожидающих заявок, но не гарантирует соблюдения сроков при перегрузке.','На каждом такте сначала освобождаются завершённые места, затем добавляются заявки и распределяются свободные места. REQUEST, GRANT, RELEASE и CONFLICT фиксируются в журнале. Ёмкость контролируется инвариантом: число активных заказов не больше числа мест.']),
('4. План эксперимента и метрики',['Проведено 120 прогонов: 20 seed (0..19), три механизма, две вместимости. Горизонт 160 тактов (0..159). В пределах одного seed входные заказы совпадают, что обеспечивает парное сравнение. Ниже показаны средние по 20 прогонам; исходные значения сохранены в results.json.','Завершено - число оконченных заказов; просрочено - число завершённых после срока; ожидание - время от поступления до выдачи места, усреднённое только по получившим место заказам. Незавершённые учитываются отдельно как pending, поэтому нулевая просрочка при нулевом выполнении не означает хороший результат. Индекс Джейна J=(сумма x)^2/(6*сумма x²), где x - число завершений каждого курьера. При отсутствии завершений в файле условно записан 0; математически индекс в этой точке не определён.','TABLE']),
('5. Анализ результатов',['Без согласования все шесть претендентов повторяют конфликт до конца горизонта. FIFO и арбитраж с приоритетом устраняют этот конфликт. При одном месте среднее выполнение составляет 44.75 из 60; средняя суммарная потребность в обслуживании около 210 тактов превышает доступный горизонт. Один лишь порядок очереди не устраняет нехватку ресурса.','При двух местах оба механизма завершают все 60 заказов. Приоритет снижает среднее число просроченных завершений с 48.90 до 47.25 (на 1.65 заказа), но при одном месте он хуже FIFO по этой метрике: 40.25 против 39.70. Следовательно, универсального преимущества приоритета эксперимент не показал. Справедливость по числу выполнений близка к 1, но она не отражает равенство времени ожидания.']),
('6. Проверки, ограничения и вывод',['Автотесты проверяют воспроизводимость, конфликт без арбитра, ограничение вместимости и завершение всех задач FIFO/priority на расширенном горизонте 500 тактов. Журналы seed=0 доступны отдельно в демонстрации.','Централизованный арбитр даёт однозначное разрешение конкуренции и обеспечивает прогресс на конечной очереди. Ограничения: нет маршрутов и переговоров о цене; все курьеры честные, длительности известны среде, арбитр не отказывает; горизонт и распределение нагрузки фиксированы. Проверка других интенсивностей, случайного отката и отказа арбитра остаётся направлением дальнейшего исследования.'])],['Мест','Механизм','Завершено','Просрочено','Ожидание','J'],rows3)
r4=json.loads((ROOT/'lab4/results.json').read_text());rows4=[]
for c in ('normal','lost_assign','lost_done','crash','forged_done','duplicate_done','stale_done'):
 for p in (False,True):
  rs=[r for r in r4 if r['scenario']==c and r['protected']==p];rows4.append([c,'да' if p else 'нет',avg(rs,'physical'),avg(rs,'reported'),avg(rs,'false_reports'),avg(rs,'rejected')])
make(4,'Надёжность взаимодействия агентов при сбоях',[
('1. Цель и модель',['Исследовать последствия потерь сообщений, отказа исполнителя и некорректных подтверждений в курьерской МАС, реализовать защитный протокол и повторно проверить выполнение заказов. Это автономная модель исполнения назначений из предметной области ЛР1-ЛР2; маршруты и очередь погрузки ЛР3 здесь не моделируются.','Диспетчер распределяет 24 готовых заказа между тремя курьерами. Каждый курьер выполняет не более одной задачи одновременно. Продолжительность - случайное целое 2..5 тактов. Среда хранит достоверный факт физического выполнения. Состояния заказа: waiting, assigned, done. Назначение содержит номер заказа, исполнителя и номер попытки.']),
('2. Неблагоприятные сценарии',['normal: штатная работа. lost_assign: теряется первое назначение, исполнитель его не начинает. lost_done: теряется первое подтверждение уже выполненного заказа. crash: первый активный курьер прекращает работу до завершения заказа и остаётся недоступным.','forged_done: посторонний участник присылает раннее подтверждение первого заказа. stale_done: назначенный курьер присылает раннее подтверждение с устаревшим номером попытки. duplicate_done: каждое подтверждение дублируется один раз. Воздействия исполняются только внутри локальной модели, без внешних сетевых обращений. Кроме duplicate_done, в каждом прогоне происходит одно воздействие.']),
('3. Протокол до и после защиты',['Базовый диспетчер принимает DONE без проверки отправителя и попытки, не использует тайм-аут. Выполненные номера хранятся в множестве, поэтому двойного увеличения счётчика нет даже в базовой версии; однако повторное сообщение обрабатывается повторно.','Защищённый диспетчер проверяет соответствие отправителя назначенному курьеру, номер попытки, состояние assigned и наличие достоверной квитанции среды. Неподходящий DONE отклоняется. После перехода в done повторное подтверждение также отклоняется.','Если через 8 тактов нет принятого подтверждения, диспетчер проверяет квитанцию. При наличии факта доставки заказ закрывается без повторного исполнения. Если факта нет, назначение отзывается и заказ возвращается в очередь; номер следующей попытки увеличивается. Отказавший курьер исключается из доступных. Тайм-аут больше максимального срока исполнения 5 тактов, поэтому в нормальном режиме не возникает ложных отзывов.','Идентификатор отправителя, состояние доступности курьера и квитанция среды считаются доверенными. Это абстракция защищённого канала, мониторинга и внешнего реестра, а не реализация цифровой подписи. При компрометации этих источников достоверности данная защита недостаточна.']),
('4. Эксперимент и метрики',['280 прогонов: 20 seed, семь сценариев, два режима. Горизонт 150 тактов. Для каждого seed длительности совпадают между режимами и сценариями. Таблица содержит средние значения. Физически - число реальных выполнений; учтено - число заказов, отмеченных done; ложных - число принятых DONE до физического выполнения; отклонено - число отвергнутых сообщений.','Конечный false_success показывает учтённые, но физически не выполненные заказы. Он не заменяет false_reports: раннее ложное подтверждение может позже скрыться за реальным выполнением. В results.json также сохранены pending, unreported, retries и число записей журнала messages. Последнее включает события среды, а не только сетевые пакеты.','TABLE']),
('5. Анализ отказов и восстановления',['Без защиты потеря назначения и отказ курьера оставляют один заказ невыполненным. Потеря DONE оставляет один реально выполненный заказ неучтённым. При ложном или устаревшем DONE базовый режим преждевременно сообщает об успехе один раз; к концу моделирования физическое выполнение догоняет отчётность, поэтому одного сравнения итоговых счётчиков недостаточно.','С защитой во всех 140 прогонах выполнены и учтены все 24 заказа, ранних ложных подтверждений не принято. Потерянное назначение и отказ вызывают один повтор назначения; потерянное подтверждение закрывается по квитанции. Дубли не повышают итоговый счётчик ни в одном режиме, а защита дополнительно отвергает 24 повторных сообщения.','Журнал seed=0 показывает причинную цепочку ASSIGN -> DROP_ASSIGN -> REVOKE -> ASSIGN с новой попыткой -> PHYSICAL_DELIVERY -> DONE. При lost_done цепочка заканчивается VERIFY_RECEIPT. Полные журналы вынесены в traces.json и интерактивный просмотр.']),
('6. Проверки, ограничения и вывод',['Тесты проверяют полное корректное завершение защищённой модели для всех сценариев и seed, наличие зависшей задачи без защиты, выявление раннего ложного успеха, отбрасывание устаревшей попытки и воспроизводимость.','Полученный результат подтверждает устойчивость только в заданной модели одиночных воздействий и доверенной среды. Не исследованы длительные сетевые разделения, массовые потери, отказ диспетчера, сговор курьеров, подделка доверенных квитанций и бесконечная нагрузка. Для реальной системы нужны аутентификация, устойчивое хранилище, протокол подтверждения доставки и безопасная отмена выполняющейся попытки.','Вывод: проверка контекста сообщения и идемпотентное завершение предотвращают преждевременный успех, а тайм-аут с проверкой квитанции восстанавливает прогресс после изученных сбоев без повторной физической доставки.'])],['Сценарий','Защита','Физически','Учтено','Ложных','Отклонено'],rows4)
