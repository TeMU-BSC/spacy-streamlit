import gettext
from pathlib import Path
from typing import List, Sequence, Tuple, Optional, Dict, Union, Callable
import streamlit as st
import spacy
from spacy.language import Language
from spacy import displacy
import pandas as pd

from .util import load_model, process_text, get_svg, get_html, Demotype, get_logo

language = gettext.translation('base', Path(__file__).resolve().parent / "locale")
language.install()
_ = language.gettext
ngettext = language.ngettext

SPACY_VERSION = tuple(map(int, spacy.__version__.split(".")))

# fmt: off
NER_ATTRS = ["text", "label_", "start", "end", "start_char", "end_char"]
TOKEN_ATTRS = ["idx", "text", "lemma_", "pos_", "tag_", "dep_", "head", "morph",
               "ent_type_", "ent_iob_", "shape_", "is_alpha", "is_ascii",
               "is_digit", "is_punct", "like_num", "is_sent_start"]
# Currently these attrs are the same, but they might differ in the future.
SPAN_ATTRS = NER_ATTRS 

# fmt: on
FOOTER = f"""<span style="font-size: 0.75em">&hearts; {_("Built with")} [`spacy-streamlit`](https://github.com/explosion/spacy-streamlit)</span>"""


def visualize(
    models: Union[List[str], Dict[str, str]],
    default_text: str = "",
    default_model: Optional[str] = None,
    visualizers: List[str] = ["parser", "ner", "textcat", "similarity", "tokens"],
    ner_labels: Optional[List[str]] = None,
    ner_attrs: List[str] = NER_ATTRS,
    similarity_texts: Tuple[str, str] = ("apple", "orange"),
    token_attrs: List[str] = TOKEN_ATTRS,
    show_json_doc: bool = True,
    show_meta: bool = True,
    show_config: bool = True,
    show_models_download_links: bool = True,
    models_download_name_links: Optional[List] = None,
    show_visualizer_select: bool = False,
    show_pipeline_info: bool = True,
    sidebar_title: Optional[str] = None,
    sidebar_description: Optional[str] = None,
    show_logo: bool = True,
    demo_type: Optional[Demotype] = None,
    ner_expander_open: bool = False,
    color: Optional[str] = "#09A3D5",
    key: Optional[str] = None,
    get_default_text: Callable[[Language], str] = None,
) -> None:
    """Embed the full visualizer with selected components."""

    # if st.config.get_option("theme.primaryColor") != color:
    #     st.config.set_option("theme.primaryColor", color)
    #
    #     # Necessary to apply theming
    #     st.experimental_rerun()

    if show_logo:
        st.sidebar.markdown(get_logo(demo_type), unsafe_allow_html=True)
    if sidebar_title:
        st.sidebar.markdown(f'## {sidebar_title}')
    if sidebar_description:
        st.sidebar.markdown(sidebar_description)

    # Allow both dict of model name / description as well as list of names
    model_names = models
    format_func = str
    if isinstance(models, dict):
        format_func = lambda name: models.get(name, name)
        model_names = list(models.keys())

    default_model_index = (
        model_names.index(default_model)
        if default_model is not None and default_model in model_names
        else 0
    )
    spacy_model = st.sidebar.selectbox(
        _("Model"),
        model_names,
        index=default_model_index,
        key=f"{key}_visualize_models",
        format_func=format_func,
    )

    if show_models_download_links and models_download_name_links is not None:
        for model_download in models_download_name_links:
            model_name = model_download["name"]
            model_link = model_download["link"]
            st.sidebar.write(f"[{_('Download the {} model').format(model_name)}]({model_link})")

    model_load_state = st.info(f"{_('Loading model')} '{spacy_model}'...")
    nlp = load_model(spacy_model)
    model_load_state.empty()

    if show_pipeline_info:
        st.sidebar.subheader(_("Pipeline info"))
        desc = f"""<p style="font-size: 0.85em; line-height: 1.5"><strong>{spacy_model}:</strong> <code>v{nlp.meta['version']}</code>. {nlp.meta.get("description", "")}</p>"""
        st.sidebar.markdown(desc, unsafe_allow_html=True)

    if show_visualizer_select:
        active_visualizers = st.sidebar.multiselect(
            "Visualizers",
            options=visualizers,
            default=list(visualizers),
            key=f"{key}_viz_select",
        )
    else:
        active_visualizers = visualizers

    st.sidebar.write(f"[{_('How to use spacy')}](https://raw.githubusercontent.com/explosion/assets/main/spaCy/spaCy-cheat-sheet.pdf)")

    default_text = (
        get_default_text(nlp) if get_default_text is not None else default_text
    )
    text = st.text_area(_("Text to analyze"), default_text, key=f"{key}_visualize_text")
    doc = process_text(spacy_model, text)

    if "ner" in visualizers and "ner" in active_visualizers:
        try:
            ner_labels = ner_labels or nlp.get_pipe("ner").labels
            visualize_ner(doc, labels=ner_labels, attrs=ner_attrs, key=key, expander_open=ner_expander_open)
        except KeyError:
            st.error(_("NER not available for this model. Please uncheck the NER visualizer in the left column to hide this message."), icon="⚠")
    if "textcat" in visualizers and "textcat" in active_visualizers:
        visualize_textcat(doc)
    if "tokens" in visualizers and "tokens" in active_visualizers:
        visualize_tokens(doc, attrs=token_attrs, key=key)
    if "parser" in visualizers and "parser" in active_visualizers:
        visualize_parser(doc, key=key)
    if "similarity" in visualizers and "similarity" in active_visualizers:
        visualize_similarity(nlp, default_texts=similarity_texts, key=key)

    if show_json_doc or show_meta or show_config:
        st.markdown(f'##### {_("Pipeline information")}')
        if show_json_doc:
            json_doc_exp = st.expander("JSON Doc")
            json_doc_exp.json(doc.to_json())

        if show_meta:
            meta_exp = st.expander("Pipeline meta.json")
            meta_exp.json(nlp.meta)

        if show_config:
            config_exp = st.expander("Pipeline config.cfg")
            config_exp.code(nlp.config.to_str())

    # st.sidebar.markdown(
    #     FOOTER,
    #     unsafe_allow_html=True,
    # )


def visualize_parser(
    doc: Union[spacy.tokens.Doc, List[Dict[str, str]]],
    *,
    title: Optional[str] = _("Dependency Parse & Part-of-speech tags"),
    key: Optional[str] = None,
    manual: bool = False,
    displacy_options: Optional[Dict] = None,
) -> None:
    """Visualizer for dependency parses.

    doc (Doc, List): The document to visualize.
    key (str): Key used for the streamlit component for selecting labels.
    title (str): The title displayed at the top of the parser visualization.
    manual (bool): Flag signifying whether the doc argument is a Doc object or a List of Dicts containing parse information.
    displacy_options (Dict): Dictionary of options to be passed to the displacy render method for generating the HTML to be rendered.
      See: https://spacy.io/api/top-level#options-dep
    """
    if displacy_options is None:
        displacy_options = dict()
    if title:
        st.markdown(f"##### {title}")
    if manual:
        # In manual mode, collapse_phrases and collapse_punct are passed as options to
        # displacy.parse_deps(doc) and the resulting data is retokenized to be correct,
        # so we already have these options configured at the time we use this data.
        cols = st.columns(1)
        split_sents = False
        options = {
            "compact": cols[0].checkbox(_("Compact mode"), key=f"{key}_parser_compact"),
        }
    else:
        cols = st.columns(4)
        split_sents = cols[0].checkbox(
            _("Split sentences"), value=True, key=f"{key}_parser_split_sents"
        )
        options = {
            "collapse_punct": cols[1].checkbox(
                _("Collapse punct"), value=True, key=f"{key}_parser_collapse_punct"
            ),
            "collapse_phrases": cols[2].checkbox(
                _("Collapse phrases"), key=f"{key}_parser_collapse_phrases"
            ),
            "compact": cols[3].checkbox(_("Compact mode"), key=f"{key}_parser_compact"),
        }
    docs = [span.as_doc() for span in doc.sents] if split_sents else [doc]
    # add selected options to options provided by user
    # `options` from `displacy_options` are overwritten by user provided
    # options from the checkboxes
    displacy_options = {**displacy_options, **options}
    for sent in docs:
        html = displacy.render(
            sent, options=displacy_options, style="dep", manual=manual
        )
        # Double newlines seem to mess with the rendering
        html = html.replace("\n\n", "\n")
        if split_sents and len(docs) > 1:
            st.markdown(f"> {sent.text}")
        st.write(get_svg(html), unsafe_allow_html=True)


def visualize_ner(
    doc: Union[spacy.tokens.Doc, List[Dict[str, str]]],
    *,
    labels: Sequence[str] = tuple(),
    attrs: List[str] = NER_ATTRS,
    show_table: bool = True,
    title: Optional[str] = _("Named Entities"),
    expander_text: Optional[str] = _("Select entity labels"),
    expander_open: bool = False,
    entity_labels_text: Optional[str] = _("Entity labels"),
    colors: Dict[str, str] = {},
    key: Optional[str] = None,
    manual: bool = False,
    displacy_options: Optional[Dict] = None,
):
    """
    Visualizer for named entities.

    doc (Doc, List): The document to visualize.
    labels (list): The entity labels to visualize.
    attrs (list):  The attributes on the entity Span to be labeled. Attributes are displayed only when the show_table
    argument is True.
    show_table (bool): Flag signifying whether to show a table with accompanying entity attributes.
    title (str): The title displayed at the top of the NER visualization.
    colors (Dict): Dictionary of colors for the entity spans to visualize, with keys as labels and corresponding colors
    as the values. This argument will be deprecated soon. In future the colors arg need to be passed in the displacy_options arg
    with the key "colors".
    key (str): Key used for the streamlit component for selecting labels.
    manual (bool): Flag signifying whether the doc argument is a Doc object or a List of Dicts containing entity span
    information.
    displacy_options (Dict): Dictionary of options to be passed to the displacy render method for generating the HTML to be rendered.
      See https://spacy.io/api/top-level#displacy_options-ent.
    """
    if not displacy_options:
        displacy_options = dict()
    if colors:
        displacy_options["colors"] = colors

    if title:
        st.markdown(f"##### {title}")

    if manual:
        if show_table:
            st.warning(
                _("When the parameter 'manual' is set to True, the parameter 'show_table' must be set to False.")
            )
        if not isinstance(doc, list):
            st.warning(
                _("When the parameter 'manual' is set to True, the parameter 'doc' must be of type 'list', not 'spacy.tokens.Doc'.")
            )
    else:
        labels = labels or list({ent.label_ for ent in doc.ents})

    if not labels:
        st.warning(_("The parameter 'labels' should not be empty or None."))
    else:
        exp = st.expander(expander_text, expanded=expander_open)
        label_select = exp.multiselect(
            entity_labels_text,
            options=labels,
            default=list(labels),
            key=f"{key}_ner_label_select",
        )

        displacy_options["ents"] = label_select
        html = displacy.render(
            doc,
            style="ent",
            options=displacy_options,
            manual=manual,
        )
        style = "<style>mark.entity { display: inline-block }</style>"
        st.write(f"{style}{get_html(html)}", unsafe_allow_html=True)
        if show_table:
            data = [
                [str(getattr(ent, attr)) for attr in attrs]
                for ent in doc.ents
                if ent.label_ in label_select
            ]
            if data:
                df = pd.DataFrame(data, columns=attrs)
                st.dataframe(df)


def visualize_spans(
    doc: Union[spacy.tokens.Doc, Dict[str, str]],
    *,
    spans_key: str = "sc",
    attrs: List[str] = SPAN_ATTRS,
    show_table: bool = True,
    title: Optional[str] = "Spans",
    manual: bool = False,
    displacy_options: Optional[Dict] = None,
):
    """
    Visualizer for spans.

    doc (Doc, Dict): The document to visualize.
    spans_key (str): Which spans key to render spans from. Default is "sc".
    attrs (list):  The attributes on the entity Span to be labeled. Attributes are displayed only when the show_table
    argument is True.
    show_table (bool): Flag signifying whether to show a table with accompanying span attributes.
    title (str): The title displayed at the top of the Spans visualization.
    manual (bool): Flag signifying whether the doc argument is a Doc object or a List of Dicts containing span information.
    displacy_options (Dict): Dictionary of options to be passed to the displacy render method for generating the HTML to be rendered.
      See https://spacy.io/api/top-level#displacy_options-span
    """
    if SPACY_VERSION < (3, 3, 0):
        raise ValueError(
            f"'visualize_spans' requires spacy>=3.3.0. You have spacy=={spacy.__version__}"
        )
    if not displacy_options:
        displacy_options = dict()
    displacy_options["spans_key"] = spans_key

    if title:
        st.markdown(f"##### {title}")

    if manual:
        if show_table:
            st.warning(
                _("When the parameter 'manual' is set to True, the parameter 'show_table' must be set to False.")
            )
        if not isinstance(doc, dict):
            st.warning(
                _("When the parameter 'manual' is set to True, the parameter 'doc' must be of type 'Dict', not 'spacy.tokens.Doc'.")
            )
    html = displacy.render(
        doc,
        style="span",
        options=displacy_options,
        manual=manual,
    )
    st.write(f"{get_html(html)}", unsafe_allow_html=True)

    if show_table:
        data = [
            [str(getattr(span, attr)) for attr in attrs]
            for span in doc.spans[spans_key]
        ]
        if data:
            df = pd.DataFrame(data, columns=attrs)
            st.dataframe(df)


def visualize_textcat(
    doc: spacy.tokens.Doc, *, title: Optional[str] = _("Text Classification")
) -> None:
    """Visualizer for text categories."""
    if title:
        st.markdown(f"##### {title}")
    st.markdown(f"> {doc.text}")
    df = pd.DataFrame(doc.cats.items(), columns=("Label", "Score"))
    df.sort_values(by=["Score"], axis=0, ascending=False,inplace=True)
    st.dataframe(df)


def visualize_similarity(
    nlp: spacy.language.Language,
    default_texts: Tuple[str, str] = ("apple", "orange"),
    *,
    threshold: float = 0.5,
    title: Optional[str] = _("Vectors & Similarity"),
    key: Optional[str] = None,
) -> None:
    """Visualizer for semantic similarity using word vectors."""
    meta = nlp.meta.get("vectors", {})
    if title:
        st.markdown(f"##### {title}")
    if not meta.get("width", 0):
        st.warning(_("No vectors available in the model."))
    else:
        cols = st.columns(2)
        text1 = cols[0].text_input(
            _("Text or word 1"), default_texts[0], key=f"{key}_similarity_text1"
        )
        text2 = cols[1].text_input(
            _("Text or word 2"), default_texts[1], key=f"{key}_similarity_text2"
        )
        doc1 = nlp.make_doc(text1)
        doc2 = nlp.make_doc(text2)
        similarity = doc1.similarity(doc2)
        similarity_text = f"**{_('Score')}:** `{similarity}`"
        if similarity > threshold:
            st.success(similarity_text)
        else:
            st.error(similarity_text)

        exp = st.expander(_("Vector information"))
        exp.code(meta)


def visualize_tokens(
    doc: spacy.tokens.Doc,
    *,
    attrs: List[str] = TOKEN_ATTRS,
    title: Optional[str] = _("Token attributes"),
    key: Optional[str] = None,
) -> None:
    """Visualizer for token attributes."""
    if title:
        st.markdown(f"##### {title}")
    exp = st.expander(_("Select token attributes"))
    selected = exp.multiselect(
        _("Token attributes"),
        options=attrs,
        default=list(attrs),
        key=f"{key}_tokens_attr_select",
    )
    data = [[str(getattr(token, attr)) for attr in selected] for token in doc]
    df = pd.DataFrame(data, columns=selected)
    st.dataframe(df)
