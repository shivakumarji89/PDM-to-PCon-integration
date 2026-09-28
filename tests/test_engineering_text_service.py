from types import SimpleNamespace

from models.article import Article
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.option import Option
from models.option_value import OptionValue
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService
from services.engineering.engineering_text_service import EngineeringTextService


def _service():
    context = SimpleNamespace()
    context.engineering_class_service = EngineeringClassService(context)
    return EngineeringTextService(context)


def test_text_workflow_captures_all_required_text_categories():
    article = Article(
        id="a1",
        product_id="p1",
        code="ABC123",
        name="Desk",
        description="Desk long description",
    )
    prop_value = PropertyValue(
        id="pv1", property_id="prop1", value="Natural Oak", code="N"
    )
    prop = Property(id="prop1", name="Top Material", values=[prop_value])
    option_value = OptionValue(
        id="ov1", option_id="opt1", value="Black", code="B"
    )
    option = Option(id="opt1", name="Frame Color", values=[option_value])
    snapshot = Snapshot(
        articles=[article],
        properties=[prop],
        options=[option],
        engineering=Engineering(
            families=[
                EngineeringFamily(
                    id="f1",
                    name="Desk",
                    members=[
                        MemberArticle(
                            id="m1",
                            article_id="a1",
                            family_id="f1",
                            short_description="Desk short",
                            long_description="Desk long",
                        )
                    ],
                )
            ]
        ),
    )

    blocks = _service().build_text_blocks(snapshot)
    keys = {(b.type_code, b.name): b.en for b in blocks}

    assert keys[("artshort", "ABC123")] == "Desk short"
    assert keys[("artlong", "ABC123")] == "Desk long"
    assert keys[("property", "Top_Material")] == "Top Material"
    assert keys[("propvalue", "Top_Material_N")] == "Natural Oak"
    assert keys[("option", "Frame_Color")] == "Frame Color"
    assert keys[("optionvalue", "Frame_Color_B")] == "Black"


def test_text_workflow_captures_articles_without_engineering_members():
    snapshot = Snapshot(
        articles=[
            Article(
                id="a1",
                product_id="p1",
                code="A100",
                name="Article",
                description="Article description",
            )
        ]
    )

    blocks = _service().build_text_blocks(snapshot)
    keys = {(b.type_code, b.name): b.en for b in blocks}

    assert keys[("artshort", "A100")] == "Article description"
    assert keys[("artlong", "A100")] == "Article description"


def test_text_workflow_keeps_values_without_codes():
    snapshot = Snapshot(
        properties=[
            Property(
                id="p1",
                name="Finish",
                values=[PropertyValue(id="v1", property_id="p1", value="Custom")],
            )
        ],
        options=[
            Option(
                id="o1",
                name="Handle",
                values=[OptionValue(id="ov1", option_id="o1", value="Custom")],
            )
        ],
    )

    blocks = _service().build_text_blocks(snapshot)
    keys = {(b.type_code, b.name): b.en for b in blocks}

    assert keys[("propvalue", "Finish_id_v1")] == "Custom"
    assert keys[("optionvalue", "Handle_id_ov1")] == "Custom"
