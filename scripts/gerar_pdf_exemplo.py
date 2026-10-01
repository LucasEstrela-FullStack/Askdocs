# /// script
# requires-python = ">=3.12"
# dependencies = ["reportlab>=4.2"]
# ///
"""Gera o PDF de exemplo para a base do AskDocs.

É o manual do colaborador de uma empresa inventada, com números, prazos e
regras bem específicos. O modelo não tem como saber nada disso de antemão,
então, quando ele acerta, a resposta veio mesmo da base.

Uso:
    uv run scripts/gerar_pdf_exemplo.py [caminho_de_saida]
"""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

SAIDA_PADRAO = Path(__file__).resolve().parent.parent / "base" / "manual-do-colaborador-nebula-labs.pdf"

INDIGO = colors.HexColor("#1E2A5A")
TEAL = colors.HexColor("#14B8A6")
TEAL_CLARO = colors.HexColor("#E6F7F5")
CINZA = colors.HexColor("#F3F4F6")
TEXTO = colors.HexColor("#1F2937")
SUAVE = colors.HexColor("#6B7280")

LARGURA, ALTURA = A4
MARGEM = 22 * mm
LARGURA_UTIL = LARGURA - 2 * MARGEM

ESTILOS = {
    "secao": ParagraphStyle(
        "Secao", fontName="Helvetica-Bold", fontSize=18, leading=22,
        textColor=INDIGO, spaceBefore=6, spaceAfter=10, keepWithNext=1,
    ),
    "titulo_sumario": ParagraphStyle(
        "TituloSumario", fontName="Helvetica-Bold", fontSize=18, leading=22,
        textColor=INDIGO, spaceAfter=10,
    ),
    "sub": ParagraphStyle(
        "Sub", fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=TEAL, spaceBefore=10, spaceAfter=4, keepWithNext=1,
    ),
    "corpo": ParagraphStyle(
        "Corpo", fontName="Helvetica", fontSize=10, leading=14.5,
        textColor=TEXTO, alignment=TA_JUSTIFY, spaceAfter=6,
    ),
    "item": ParagraphStyle(
        "Item", fontName="Helvetica", fontSize=10, leading=14.5,
        textColor=TEXTO, leftIndent=12, bulletIndent=2, spaceAfter=3,
    ),
    "celula": ParagraphStyle(
        "Celula", fontName="Helvetica", fontSize=9, leading=12, textColor=TEXTO,
    ),
    "cabecalho": ParagraphStyle(
        "Cabecalho", fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=colors.white,
    ),
    "destaque": ParagraphStyle(
        "Destaque", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INDIGO,
    ),
    "pergunta": ParagraphStyle(
        "Pergunta", fontName="Helvetica-Bold", fontSize=10, leading=14,
        textColor=INDIGO, spaceBefore=8, spaceAfter=2,
    ),
}


class Manual(BaseDocTemplate):
    """Documento com capa, sumario automatico e marcadores por secao."""

    def __init__(self, caminho: Path) -> None:
        super().__init__(
            str(caminho), pagesize=A4,
            leftMargin=MARGEM, rightMargin=MARGEM,
            topMargin=MARGEM + 6 * mm, bottomMargin=MARGEM,
            title="Manual do Colaborador - Nebula Labs",
            author="Nebula Labs (empresa ficticia)",
            subject="Documento ficticio para testes do AskDocs",
        )
        quadro = Frame(MARGEM, MARGEM, LARGURA_UTIL, ALTURA - 2 * MARGEM - 6 * mm, id="quadro")
        self.addPageTemplates([
            PageTemplate(id="capa", frames=[quadro], onPage=desenhar_capa),
            PageTemplate(id="conteudo", frames=[quadro], onPage=desenhar_moldura),
        ])

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name == "Secao":
            titulo = flowable.getPlainText()
            chave = "s" + titulo.split(".")[0]
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(titulo, chave, level=0)
            self.notify("TOCEntry", (0, titulo, self.page, chave))


def desenhar_capa(canv, _doc) -> None:
    canv.saveState()
    canv.setFillColor(INDIGO)
    canv.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)
    canv.setFillColor(TEAL)
    canv.rect(0, ALTURA * 0.42, LARGURA, 5 * mm, stroke=0, fill=1)
    canv.circle(LARGURA - 40 * mm, ALTURA - 55 * mm, 22 * mm, stroke=0, fill=1)
    canv.setFillColor(INDIGO)
    canv.circle(LARGURA - 33 * mm, ALTURA - 50 * mm, 19 * mm, stroke=0, fill=1)

    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 13)
    canv.drawString(MARGEM, ALTURA - 40 * mm, "NEBULA LABS")
    canv.setFont("Helvetica-Bold", 38)
    canv.drawString(MARGEM, ALTURA * 0.42 + 40 * mm, "Manual do")
    canv.drawString(MARGEM, ALTURA * 0.42 + 24 * mm, "Colaborador")
    canv.setFont("Helvetica", 13)
    canv.setFillColor(TEAL_CLARO)
    canv.drawString(MARGEM, ALTURA * 0.42 + 12 * mm, "Regras, benefícios e rotinas de quem faz a Nebula acontecer")

    canv.setFillColor(colors.white)
    canv.setFont("Helvetica", 11)
    canv.drawString(MARGEM, ALTURA * 0.42 - 15 * mm, "Versão 3.2  ·  Vigente desde 1º de março de 2026")
    canv.drawString(MARGEM, ALTURA * 0.42 - 22 * mm, "Responsável: Pessoas & Cultura")

    canv.setFillColor(TEAL)
    canv.setFont("Helvetica-Oblique", 9)
    canv.drawString(
        MARGEM, MARGEM,
        "Documento fictício criado para testes do AskDocs. Empresa, pessoas e valores são inventados.",
    )
    canv.restoreState()


def desenhar_moldura(canv, doc) -> None:
    canv.saveState()
    canv.setStrokeColor(TEAL)
    canv.setLineWidth(1.2)
    canv.line(MARGEM, ALTURA - MARGEM, LARGURA - MARGEM, ALTURA - MARGEM)
    canv.setFont("Helvetica-Bold", 8.5)
    canv.setFillColor(INDIGO)
    canv.drawString(MARGEM, ALTURA - MARGEM + 3 * mm, "NEBULA LABS")
    canv.setFont("Helvetica", 8.5)
    canv.setFillColor(SUAVE)
    canv.drawRightString(LARGURA - MARGEM, ALTURA - MARGEM + 3 * mm, "Manual do Colaborador  ·  v3.2")

    canv.setStrokeColor(CINZA)
    canv.line(MARGEM, MARGEM - 6 * mm, LARGURA - MARGEM, MARGEM - 6 * mm)
    canv.drawString(MARGEM, MARGEM - 11 * mm, "Documento fictício para testes do AskDocs")
    canv.drawRightString(LARGURA - MARGEM, MARGEM - 11 * mm, f"Página {doc.page}")
    canv.restoreState()


def p(texto: str, estilo: str = "corpo") -> Paragraph:
    return Paragraph(texto, ESTILOS[estilo])


def lista(*itens: str) -> list[Paragraph]:
    return [Paragraph(item, ESTILOS["item"], bulletText="•") for item in itens]


def destaque(texto: str) -> Table:
    caixa = Table([[Paragraph(texto, ESTILOS["destaque"])]], colWidths=[LARGURA_UTIL])
    caixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_CLARO),
        ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 4), caixa, Spacer(1, 8)])


def tabela(cabecalho: list[str], linhas: list[list[str]], larguras: list[float]) -> Table:
    dados = [[Paragraph(c, ESTILOS["cabecalho"]) for c in cabecalho]]
    dados += [[Paragraph(c, ESTILOS["celula"]) for c in linha] for linha in linhas]
    t = Table(dados, colWidths=[LARGURA_UTIL * f for f in larguras], repeatRows=1, hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, -1), (-1, -1), 1, TEAL),
    ]
    estilo += [("BACKGROUND", (0, i), (-1, i), CINZA) for i in range(2, len(dados), 2)]
    t.setStyle(TableStyle(estilo))
    return KeepTogether([t, Spacer(1, 10)])


def secao(titulo: str) -> Paragraph:
    return p(titulo, "secao")


def conteudo() -> list:
    sumario = TableOfContents()
    sumario.levelStyles = [ParagraphStyle(
        "Sumario", fontName="Helvetica", fontSize=11, leading=20, textColor=TEXTO,
        leftIndent=0, firstLineIndent=0,
    )]
    sumario.dotsMinLevel = 0

    h = [Spacer(1, 1), NextPageTemplate("conteudo"), PageBreak()]

    h += [p("Sumário", "titulo_sumario"), Spacer(1, 6), sumario, PageBreak()]

    h += [
        secao("1. Sobre a Nebula Labs"),
        p("A Nebula Labs é uma empresa de tecnologia fundada em <b>2019</b>, em "
          "<b>Florianópolis (SC)</b>, por Helena Vasconcelos e Rafael Antunes. Desenvolvemos "
          "plataformas de análise de dados para cooperativas agrícolas e contamos hoje com "
          "<b>84 colaboradores</b> distribuídos em 11 estados brasileiros."),
        p("Nossa missão é <i>transformar dados do campo em decisões simples</i>. Nossos três "
          "valores guiam todas as decisões descritas neste manual:"),
        *lista(
            "<b>Clareza antes de velocidade</b>: preferimos entender o problema a entregar rápido a solução errada.",
            "<b>Autonomia com responsabilidade</b>: cada pessoa decide como trabalha e responde pelo resultado.",
            "<b>Gente cuida de gente</b>: benefícios e regras existem para proteger quem está aqui.",
        ),
        p("Este manual vale para todas as pessoas contratadas em regime CLT. Estagiários e "
          "prestadores de serviço seguem regras próprias, descritas nos respectivos contratos."),
        destaque("<b>Dúvidas sobre este manual?</b> Fale com a equipe de Pessoas &amp; Cultura pelo "
                 "e-mail pessoas@nebulalabs.example ou pelo canal #pessoas no chat interno."),

        secao("2. Jornada de trabalho"),
        p("A jornada contratual é de <b>40 horas semanais</b>, de segunda a sexta-feira. Não "
          "controlamos horário de entrada e saída, mas todas as pessoas devem estar disponíveis "
          "no <b>horário núcleo, das 10h às 16h</b>, quando acontecem as reuniões entre equipes."),
        p("Modelo híbrido", "sub"),
        p("Trabalhamos no modelo híbrido: <b>três dias remotos e dois presenciais</b>. Os dias de "
          "escritório são fixos para toda a empresa, <b>terça e quinta-feira</b>, para garantir que "
          "as equipes se encontrem. Quem mora a mais de 100 km do escritório pode trabalhar "
          "100% remoto, com aprovação da liderança direta."),
        p("Banco de horas", "sub"),
        p("Horas extras aprovadas previamente vão para o banco de horas. O saldo deve ser "
          "compensado em até <b>6 meses</b>; depois desse prazo, as horas não compensadas são "
          "pagas na folha seguinte com adicional de 50%. O limite de saldo positivo é de "
          "<b>40 horas</b>."),
        destaque("Reuniões internas não podem ser marcadas antes das 9h nem depois das 18h, e "
                 "<b>sexta-feira à tarde é livre de reuniões</b> para todas as equipes."),

        secao("3. Férias e ausências"),
        p("Toda pessoa tem direito a <b>30 dias de férias</b> a cada 12 meses trabalhados, com "
          "o adicional de um terço do salário previsto em lei."),
        *lista(
            "As férias podem ser divididas em <b>até três períodos</b>.",
            "Um dos períodos deve ter <b>no mínimo 14 dias corridos</b>; os demais, no mínimo 5 dias.",
            "O pedido deve ser feito com <b>45 dias de antecedência</b> pelo portal Pessoas.",
            "É possível vender até 10 dias (abono pecuniário), informando no próprio pedido.",
            "Férias não podem começar nos dois dias que antecedem feriado ou fim de semana.",
        ),
        p("Outras ausências", "sub"),
        tabela(
            ["Situação", "Dias de folga", "Como comprovar"],
            [
                ["Aniversário (day off)", "1 dia, no mês do aniversário", "Basta avisar a liderança"],
                ["Casamento", "5 dias úteis", "Certidão de casamento"],
                ["Nascimento ou adoção (licença parental)", "120 dias, para qualquer gênero", "Certidão ou termo de guarda"],
                ["Falecimento de familiar próximo", "5 dias corridos", "Certidão de óbito"],
                ["Doação de sangue", "1 dia por ano", "Comprovante do hemocentro"],
                ["Mudança de casa", "2 dias", "Comprovante de endereço novo"],
            ],
            [0.38, 0.32, 0.30],
        ),

        secao("4. Benefícios"),
        p("Os benefícios começam a valer no primeiro dia de trabalho, exceto o auxílio "
          "educação, que exige 3 meses de casa. Todos os valores abaixo são mensais, salvo "
          "indicação contrária."),
        tabela(
            ["Benefício", "Valor ou cobertura", "Observações"],
            [
                ["Vale-refeição ou alimentação", "R$ 1.250,00 por mês", "A pessoa escolhe a divisão entre VR e VA"],
                ["Plano de saúde", "100% pago para a pessoa titular", "Dependentes com 50% de desconto"],
                ["Plano odontológico", "100% pago para titular e dependentes", "Sem carência"],
                ["Auxílio home office", "R$ 180,00 por mês", "Para internet e energia"],
                ["Auxílio educação", "Até R$ 6.000,00 por ano", "Cursos ligados à função; exige 3 meses de casa"],
                ["Bem-estar", "Plano de academias parceiras", "Plano básico pago pela empresa"],
                ["Seguro de vida", "24 salários", "Sem custo para a pessoa"],
                ["Participação nos lucros (PLR)", "Até 1,5 salário por ano", "Paga em março, conforme as metas"],
            ],
            [0.30, 0.34, 0.36],
        ),
        destaque("O kit de boas-vindas inclui cadeira ergonômica e monitor de 27 polegadas, "
                 "entregues em casa em até <b>10 dias úteis</b> após a admissão."),

        secao("5. Reembolso de despesas"),
        p("Despesas de trabalho pagas do próprio bolso são reembolsadas pelo sistema "
          "<b>Caixa Rápida</b>. O pedido deve ser enviado em até <b>30 dias</b> após a "
          "despesa, com nota fiscal em nome da Nebula Labs. Pedidos fora do prazo são recusados "
          "automaticamente."),
        tabela(
            ["Tipo de despesa", "Limite", "Aprovação"],
            [
                ["Hospedagem em viagem", "R$ 380,00 por noite", "Automática dentro do limite"],
                ["Alimentação em viagem", "R$ 120,00 por dia", "Automática dentro do limite"],
                ["Transporte por aplicativo", "Sem limite fixo", "Apenas em viagens ou após as 22h"],
                ["Quilometragem com carro próprio", "R$ 1,10 por km", "Informar trajeto no pedido"],
                ["Qualquer despesa acima de R$ 500,00", "-", "Exige aprovação da liderança direta"],
            ],
            [0.36, 0.28, 0.36],
        ),
        p("O pagamento é feito na <b>quinzena seguinte à aprovação</b>, por depósito na conta "
          "salário. Bebidas alcoólicas, multas de trânsito e despesas pessoais não são "
          "reembolsadas em nenhuma hipótese."),

        secao("6. Segurança da informação"),
        p("Lidamos com dados de milhares de produtores rurais. Por isso, as regras abaixo são "
          "obrigatórias e o descumprimento pode levar a medidas disciplinares."),
        *lista(
            "Senhas devem ter <b>no mínimo 14 caracteres</b> e ficar no gerenciador de senhas da empresa.",
            "A <b>autenticação em dois fatores (MFA)</b> é obrigatória em todos os sistemas.",
            "O notebook deve bloquear a tela automaticamente após <b>5 minutos</b> sem uso.",
            "É proibido salvar dados de clientes em pendrives ou em contas pessoais de nuvem.",
            "Redes Wi-Fi públicas só podem ser usadas com a VPN da empresa ligada.",
        ),
        destaque("<b>Incidentes</b>, como perda do notebook, e-mail suspeito ou vazamento de dados, devem ser "
                 "comunicados em até <b>2 horas</b> no canal #seguranca ou pelo telefone de plantão "
                 "(48) 3000-0000. Avisar rápido nunca gera punição."),

        secao("7. Equipamentos"),
        p("Cada pessoa recebe um notebook configurado pela equipe de TI. Os equipamentos são "
          "trocados a cada <b>3 anos</b>, ou antes em caso de defeito sem conserto. Pedidos de "
          "periféricos extras (mouse, teclado, headset) são feitos pelo portal de TI e "
          "atendidos em até 5 dias úteis."),
        p("No desligamento, todos os equipamentos devem ser devolvidos em até <b>5 dias úteis</b>. "
          "A empresa envia uma transportadora para a retirada, sem custo para a pessoa."),

        secao("8. Avaliação e crescimento"),
        p("A avaliação de desempenho é <b>semestral</b>, nos meses de <b>março e setembro</b>. "
          "Ela combina autoavaliação, avaliação da liderança e a opinião de dois colegas "
          "escolhidos pela própria pessoa. A nota vai de <b>1 a 5</b>."),
        p("Toda pessoa monta, junto com a liderança, um <b>PDI (Plano de Desenvolvimento "
          "Individual)</b> com até três objetivos para o semestre. Promoções e reajustes por "
          "mérito acontecem apenas no ciclo de setembro, para quem tiver nota igual ou superior "
          "a 4 nos dois últimos ciclos."),
        tabela(
            ["Nota", "Significado"],
            [
                ["1", "Abaixo do esperado em quase todos os objetivos"],
                ["2", "Abaixo do esperado em parte dos objetivos"],
                ["3", "Entregou o esperado para a função"],
                ["4", "Superou o esperado em parte dos objetivos"],
                ["5", "Referência para a equipe; superou todos os objetivos"],
            ],
            [0.15, 0.85],
        ),

        secao("9. Canais de contato"),
        tabela(
            ["Assunto", "Canal", "Prazo de resposta"],
            [
                ["Folha de pagamento e benefícios", "pessoas@nebulalabs.example", "2 dias úteis"],
                ["Problemas com notebook ou acessos", "Portal de TI ou #suporte-ti", "4 horas úteis"],
                ["Incidentes de segurança", "#seguranca ou (48) 3000-0000", "Imediato, 24 horas por dia"],
                ["Reembolsos", "Sistema Caixa Rápida", "5 dias úteis para análise"],
                ["Denúncias e ética", "Canal Confidencial (anônimo)", "10 dias úteis"],
            ],
            [0.36, 0.38, 0.26],
        ),

        secao("10. Perguntas frequentes"),
    ]

    perguntas = [
        ("Posso emendar minhas férias com um feriado?",
         "Não. As férias não podem começar nos dois dias que antecedem feriado ou fim de semana. "
         "Elas podem terminar perto de um feriado normalmente."),
        ("Mudei de cidade. Posso trabalhar 100% remoto?",
         "Sim, se a nova cidade ficar a mais de 100 km do escritório e a liderança direta aprovar."),
        ("Perdi o prazo de 30 dias do reembolso. E agora?",
         "O sistema Caixa Rápida recusa automaticamente pedidos fora do prazo, e não há exceção."),
        ("Quando posso usar o auxílio educação?",
         "A partir de 3 meses de casa, para cursos ligados à função, até R$ 6.000,00 por ano."),
        ("Quanto tempo tenho para avisar sobre um notebook perdido?",
         "Até 2 horas, no canal #seguranca ou no telefone de plantão. Avisar rápido nunca gera punição."),
        ("Quando sai a PLR?",
         "A participação nos lucros é paga em março, em valor de até 1,5 salário, conforme as metas do ano."),
    ]
    for pergunta, resposta in perguntas:
        h.append(KeepTogether([p(pergunta, "pergunta"), p(resposta)]))

    return h


def main() -> None:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA_PADRAO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Manual(caminho).multiBuild(conteudo())
    print(f"PDF gerado em {caminho}")


if __name__ == "__main__":
    main()
