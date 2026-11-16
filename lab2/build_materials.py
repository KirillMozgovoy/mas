"""Build report and offline viewer from saved experiment outputs."""
import csv
import html
import json
import statistics
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
FONT_DIR=Path('/usr/share/fonts/truetype/dejavu')
for name,f in [('DV','DejaVuSans.ttf'),('DVB','DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT_DIR/f)))
pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DV',boldItalic='DVB')
styles={k:ParagraphStyle(k,fontName='DVB' if k in ('title','h') else 'DV',fontSize=size,leading=leading,textColor=colors.HexColor('#18344c'),spaceAfter=space) for k,size,leading,space in [('title',22,29,18),('h',13,19,12),('p',10,15,10),('small',8,11,5)]}
summary=json.loads((ROOT/'results/summary.json').read_text()); rows=list(csv.DictReader((ROOT/'results/runs.csv').open()))
labels={'sparse':'Интервал 4','stream':'Интервал 1','burst':'Пакет 60'}
short={'round_robin':'RR','nearest':'MIN','contract_net':'CNET'}
story=[];md=[]
def p(s,style='p'):
    story.append(Paragraph(s,styles[style]));md.append(s.replace('<br/>','\n'))
def page(title):
    if story:story.append(PageBreak())
    p(title,'title')
def table(headers,data,widths):
    allrows=[[Paragraph(html.escape(str(c)),styles['small']) for c in row] for row in [headers]+data]
    t=Table(allrows,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#ccd8e2')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);story.append(Spacer(1,12));md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in data))
def mean(i,m):return i[m]['mean']
page('Лабораторная работа №2')
p('Исследование механизмов распределения задач и координации','h')
p('<b>Курс:</b> Теория многоагентных систем<br/><b>Выполнил:</b> Мозговой Кирилл Сергеевич<br/><b>Группа:</b> Б24-517')
p('1. Задача и цель','h')
p('Исследуется МАС доставки из ЛР1: источник формирует заказы, диспетчер распределяет их между курьерами, а курьеры принимают назначения, забирают и доставляют груз. Цель - сравнить механизмы распределения по времени обслуживания и стоимости координации на одинаковых входных данных.')
p('Реализованы три варианта: централизованный round_robin (RR), централизованный выбор минимальной оценки маршрута nearest (MIN), контрактная сеть contract_net (CNET). Прототип сохранён в отдельной папке lab2, работа lab1 не изменяется.')
p('Критерии исследования','h')
p('Проверить влияние механизма на завершение 60 заказов, среднее и хвостовое время доставки, опоздания и пройденный путь. Отдельно измерить все сообщения и сообщения координации, оценить их объём. Проверить влияние нагрузки и числа агентов.')
p('Архитектура','h')
p('Источник и диспетчер имеют разные роли; курьеры являются самостоятельными агентами. Каждый хранит позицию, скорость, грузоподъёмность и состояние исполнения. Курьер самостоятельно отклоняет назначение при занятости или превышении массы. FIFO-шина доставляет сообщения в одном процессе; прямое изменение состояния другого агента не используется.')
p('Источник требований: "Лабораторные-МАС.pdf", с. 1-2. Требования ЛР2: реализация и экспериментальное сравнение не менее двух механизмов, анализ времени выполнения, сообщений и затрат координации. Исходники и демонстрация: https://github.com/KirillMozgovoy/mas/tree/main/lab2','small')
page('2. Механизмы и протоколы')
p('Общие правила','h')
p('Очередь заказов сортируется по времени поступления, затем по ID. Один курьер выполняет один заказ. Время дискретное; расстояние манхэттенское. За такт курьер проходит не более speed единиц пути, сначала по x, затем по y. Погрузка и выгрузка мгновенные, завершение фиксируется в конце такта. При равенстве оценок выбирается минимальный ID.')
table(['Механизм','Выбор исполнителя','Обмен при назначении'],[
['RR','По циклическому указателю среди свободных курьеров с достаточной грузоподъёмностью. Указатель сдвигается после выбора.','ASSIGN -> ACCEPT'],
['MIN','Диспетчер минимизирует (d(позиция, получение) + d(получение, доставка)) / speed. Использует профили и STATUS.','ASSIGN -> ACCEPT'],
['CNET','Курьеры рассчитывают ту же оценку локально. Диспетчер выбирает минимальную полученную заявку.','CFP -> PROPOSE / REFUSE -> ASSIGN / NOT_SELECTED -> ACCEPT']],[48,244,207])
p('Контрактная сеть','h')
p('Для каждого ожидающего заказа диспетчер рассылает CFP всем курьерам. Свободный подходящий курьер отвечает PROPOSE с оценкой маршрута, остальные - REFUSE. Из предложений выбирается победитель; остальные участники получают NOT_SELECTED. Победитель получает ASSIGN и подтверждает его ACCEPT. Если предложений нет, заказ остаётся в очереди.')
p('Раунды обрабатываются последовательно и завершаются в рамках одного такта. Подтверждение назначения выполняется до следующего раунда, поэтому один курьер не выигрывает два одновременных заказа. При пустом раунде запрос повторяется на следующем такте. Это упрощённый синхронный вариант контрактной сети; таймауты, встречные предложения и сетевые потери не моделируются.')
p('Выполнение общего заказа: REQUEST -> назначение -> ACCEPT -> PICKED_UP -> DELIVERED. STATUS передаёт актуальную позицию и занятость после каждого активного такта. Повторный ASSIGN принятого заказа не запускает второе исполнение.')
page('3. Методика эксперимента')
table(['Параметр','Значение'],[
['Размер серии','3 режима x 2 размера парка x 20 seeds x 3 механизма = 360 прогонов'],
['Заказы','60 на прогон; масса равномерно от 1 до 6, координаты от 0 до 19 по каждой оси'],
['Поступление','sparse: один заказ раз в 4 такта; stream: каждый такт; burst: все 60 в такт 0'],
['Срок доставки','release + 35; опоздание не отменяет исполнение'],
['Парк','3 или 6 курьеров. Профили (capacity, speed): (3,1), (6,1), (4,2), с повторением для 6'],
['Генератор','random.Random(seed), seed = 0..19. Исходные позиции также случайные'],
['Горизонт','5000 тактов; остановка после завершения всех заказов'],
['Связь','Надёжная FIFO; нулевая задержка; обработка сообщений не расходует модельные такты']],[116,383])
p('Для каждого сочетания нагрузки, размера парка и seed один и тот же набор передаётся всем трём механизмам. Наборы и SHA-256 сохранены в results/inputs.json.gz, построчные метрики - в runs.csv. Случайность касается входов; сами механизмы детерминированы. Название sparse означает только больший интервал поступления и не гарантирует отсутствия перегрузки.')
p('Определения метрик','h')
p('T - время от такта 0 до последней доставки. L - среднее время заказа (completion - release). P95 - элемент с номером ceil(0.95n) в отсортированном списке длительностей. Late - число completion > deadline. Путь - сумма пройденных курьерами единиц расстояния.')
p('M - все сообщения. C - CFP, PROPOSE, REFUSE, NOT_SELECTED, ASSIGN, ACCEPT и REJECT; события выполнения и STATUS в C не включены. V - сумма длин компактных JSON-представлений сообщений C в байтах UTF-8, включая отправителя, адресата, время и данные. Это оценка объёма обмена без заголовков сетевого транспорта. CV - стандартное отклонение числа назначений между курьерами, делённое на среднее.')
p('Для каждого показателя сохранены среднее, выборочное стандартное отклонение и ориентировочный 95%-й t-интервал среднего: mean +/- 2.093 * sd / sqrt(20). Для сравнения RR и MIN использованы парные разности на одинаковых seeds. Время процессора и стоимость в рублях не измеряются.')
page('4. Результаты: обслуживание')
p('Во всех 360 прогонах завершены все 60 заказов. Ниже приведены средние по 20 seeds. RR - циклическое назначение; MIN - оценка диспетчера; CNET - контрактная сеть. Время измеряется в условных тактах.','small')
data=[]
for i in summary:
    data.append([labels[i['load']],i['fleet'],short[i['policy']],f"{mean(i,'makespan'):.2f}",f"{mean(i,'mean_time'):.2f}",f"{mean(i,'p95'):.2f}",f"{mean(i,'late'):.2f}",f"{mean(i,'travel'):.1f}"])
table(['Режим','N','Метод','T','L','P95','Late','Путь'],data,[77,23,44,57,57,57,52,75])
p('MIN и CNET дали одинаковые назначения и времена завершения во всех 120 парных наборах. Это ожидаемый результат: формула оценки и правило разрешения равенства совпадают, сведения о состоянии актуальны, а связь не занимает модельное время. В CNET оценку вычисляет курьер, в MIN - диспетчер. Различается место принятия локального решения и объём обмена.')
p('Переход от 3 к 6 курьерам сокращает очередь. При 3 курьерах даже интервал 4 создаёт перегрузку: среднее время заказа превышает 100 тактов. Для MIN при 6 курьерах среднее L составляет 30.99, 85.63 и 112.15 для трёх режимов соответственно.')
page('5. Цена координации и вариативность')
data=[]
for i in summary:
    data.append([labels[i['load']],i['fleet'],short[i['policy']],f"{mean(i,'messages'):.0f}",f"{mean(i,'coordination'):.0f}",f"{mean(i,'coordination_bytes')/1024:.1f}",f"{mean(i,'assignment_cv'):.3f}"])
table(['Режим','N','Метод','M','C','V, KiB','CV'],data,[77,23,44,87,87,66,58])
p('У RR и MIN C = 120: одно назначение и одно подтверждение на каждый из 60 заказов. У CNET много отказов и повторных раундов, пока курьеры заняты. Для одного раунда при n курьерах и b предложениях: 2n сообщений запроса и ответа; при b > 0 ещё b - 1 уведомлений проигравшим и 2 сообщения назначения и подтверждения, итого 2n + b + 1. При b = 0 - ровно 2n.')
p('Число сообщений CNET зависит от длительности очереди, а не только от числа доставок. Нулевое время связи скрывает эти затраты в показателях T и L. Поэтому равенство времени выполнения не означает равную вычислительную или сетевую стоимость. CV учитывает только количество заказов, без их массы и длины маршрута; он не является полной мерой справедливости.','small')
page('6. Анализ и выводы')
p('Парное сравнение MIN с RR','h')
data=[]
for load in labels:
    for fleet in (3,6):
        dif=[]
        for seed in range(20):
            g=[r for r in rows if r['load']==load and int(r['fleet'])==fleet and int(r['seed'])==seed]
            a=next(r for r in g if r['policy']=='round_robin');b=next(r for r in g if r['policy']=='nearest')
            dif.append(float(b['mean_time'])-float(a['mean_time']))
        avg=statistics.mean(dif);ci=2.093*statistics.stdev(dif)/20**.5
        data.append([labels[load],fleet,f'{avg:.2f}',f'[{avg-ci:.2f}; {avg+ci:.2f}]'])
table(['Режим','Курьеры','Разность L: MIN - RR','95% интервал'],data,[100,65,170,164])
p('Отрицательная разность означает меньшее время заказа у MIN. Небольшие средние отличия нельзя считать универсальным преимуществом: проверять следует парные интервалы. Для парка из 3 курьеров очередь и ограничения массы во многом определяют назначения; локальная минимизация маршрута не оптимизирует весь план и может ухудшить будущие назначения.')
p('Выводы','h')
p('1. Реализованы и экспериментально сравнены три механизма, включая два различных протокола координации: прямое централизованное назначение и контрактная сеть с локальными заявками курьеров.')
p('2. При полной актуальной информации, нулевой задержке и общей целевой функции MIN и CNET одинаковы по доставке. Контрактная сеть не даёт выигрыша в этих условиях, но создаёт существенно больше сообщений из-за рассылок и повторов.')
p('3. На исследованных входах увеличение парка оказывает более сильное влияние на задержки, чем смена RR на MIN. Дедлайны напрямую не участвуют в выборе заказов, поэтому при перегрузке доля опозданий высока.')
p('4. Для данной модели рационально централизованное MIN: оно обеспечивает ту же доставку, что CNET, при меньшем обмене. При приватных либо меняющихся знаниях курьеров контрактная сеть может быть полезна, но её преимущество в этой работе не доказано.')
p('Ограничения и продолжение','h')
p('Результаты относятся к данной сетке, генератору и профилям. CNET использует частые повторы без backoff; оптимизация повторов требует отдельного сравнения. Нет задержек связи, отказов, затрат на обработку сообщений и планирования нескольких заказов. Возможное продолжение - событийный повтор CFP, модель сети и учёт дедлайнов. Эти изменения не входят в выполненные эксперименты.')
def footer(c,d):
    c.setFont('DV',8);c.setFillColor(colors.HexColor('#52718a'));c.drawString(48,27,'МАС | ЛР2 | Мозговой К. С. | Б24-517');c.drawRightString(547,27,str(d.page))
SimpleDocTemplate(str(ROOT/'report.pdf'),pagesize=(595,842),leftMargin=48,rightMargin=48,topMargin=40,bottomMargin=48,title='МАС - лабораторная работа №2',author='Мозговой Кирилл Сергеевич').build(story,onFirstPage=footer,onLaterPages=footer)
(ROOT/'report.md').write_text('\n\n'.join(md),encoding='utf-8')
# Keep the browser view compact; full traces can be regenerated separately.
tracepath=ROOT/'demo/traces.json'
if tracepath.exists():
    examples=json.loads(tracepath.read_text())
    previews=[dict(scenario=r['scenario'],policy=r['policy'],metrics=r['metrics'],total_messages=len(r['trace']),trace=r['trace'][:120]) for r in examples]
    (ROOT/'demo/previews.json').write_text(json.dumps(previews,ensure_ascii=False,indent=2))
else:previews=json.loads((ROOT/'demo/previews.json').read_text())
viewer='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>МАС - ЛР2</title><style>body{font:16px/1.5 system-ui;background:#edf2f7;color:#18344c;max-width:1200px;margin:30px auto;padding:20px}section{background:white;padding:24px;border-radius:14px;margin:20px 0}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:8px;border-bottom:1px solid #d4dee8}select{padding:8px}pre{white-space:pre-wrap}.scroll{overflow:auto;max-height:550px}</style><h1>Распределение заказов между курьерами</h1><p>ЛР2 - Мозговой Кирилл Сергеевич, Б24-517. 360 прогонов, 20 seeds на условие.</p><section><h2>Сравнение средних</h2><label>Нагрузка <select id="load"><option>sparse</option><option>stream</option><option>burst</option></select></label> <label>Курьеры <select id="fleet"><option>3</option><option>6</option></select></label><div class="scroll"><table id="summary"></table></div><p>T и L - условные такты. C - сообщения координации; V - их объём в KiB UTF-8. Интервал +/- приведён для среднего L (95%, t, n=20).</p></section><section><h2>Примеры обмена сообщениями</h2><select id="example"></select><pre id="metrics"></pre><p id="note"></p><div class="scroll"><table id="trace"></table></div></section><script>const summary=__SUMMARY__,examples=__EXAMPLES__;
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const row=a=>'<tr>'+a.map(x=>'<td>'+esc(x)+'</td>').join('')+'</tr>';
const head=a=>'<tr>'+a.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr>';
function show(){const a=summary.filter(x=>x.load===document.querySelector('#load').value&&x.fleet===+document.querySelector('#fleet').value);document.querySelector('#summary').innerHTML=head(['Метод','T','L +/- CI','P95','Опозданий','M','C','V, KiB'])+a.map(x=>row([x.policy,x.makespan.mean.toFixed(2),x.mean_time.mean.toFixed(2)+' +/- '+x.mean_time.ci95.toFixed(2),x.p95.mean.toFixed(2),x.late.mean.toFixed(2),x.messages.mean.toFixed(0),x.coordination.mean.toFixed(0),(x.coordination_bytes.mean/1024).toFixed(1)])).join('');}
document.querySelector('#example').innerHTML=examples.map((x,i)=>'<option value="'+i+'">'+esc(x.scenario+' / '+x.policy+' / seed 0 / 3 курьера')+'</option>').join('');
function trace(){let x=examples[+document.querySelector('#example').value];document.querySelector('#metrics').textContent=JSON.stringify(x.metrics,null,2);document.querySelector('#note').textContent='Первые '+x.trace.length+' из '+x.total_messages+' сообщений. Полный журнал: python run_experiments.py -> demo/traces.json.';document.querySelector('#trace').innerHTML=head(['Такт','От','Кому','Тип','Данные'])+x.trace.map(m=>row([m.time,m.sender,m.receiver,m.kind,JSON.stringify(m.payload)])).join('');}
document.querySelector('#load').onchange=show;document.querySelector('#fleet').onchange=show;document.querySelector('#example').onchange=trace;show();trace();</script></html>'''
(ROOT/'demo/index.html').write_text(viewer.replace('__SUMMARY__',json.dumps(summary,ensure_ascii=False)).replace('__EXAMPLES__',json.dumps(previews,ensure_ascii=False)),encoding='utf-8')
print('Built report.pdf, report.md, demo/index.html')
