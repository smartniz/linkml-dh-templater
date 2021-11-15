import click
import linkml.utils.rawloader as rl
import pandas as pd
import yaml
from linkml_runtime.utils.schemaview import SchemaView

dh_cols = [
    'Ontology ID', 'parent class', 'label', 'datatype', 'source', 'data status', 'requirement', 'min value',
    'max value', 'capitalize', 'pattern', 'description', 'guidance', 'examples']

# default value is None
# would DataHarmonizer prefer something else?
blank_row = dict.fromkeys(dh_cols)

row_list = []

sect_set = set()

default_sect_val = 'default'


def parse_yaml_file(yaml_file_name):
    with open(yaml_file_name, 'r') as stream:
        try:
            parse_res = yaml.safe_load(stream)
            return parse_res
        except yaml.YAMLError as exc:
            print(exc)


def dict_to_schema(dict_param):
    converted_schema = rl.load_raw_schema(dict_param)
    return converted_schema


def s2sv(schema_param):
    sv = SchemaView(schema_param)
    return sv


@click.command()
@click.option('--linkml', help="path to LinkML YAML file", type=click.Path(exists=True), required=True)
@click.option('--classname', help="class to represent with DataHarmonizer", required=True)
@click.option('--dh', help="name for DH output", required=True, type=click.Path())
def l2dh_cli(linkml, classname, dh):
    """CLI wrapper for converting LinkML to DataHarmonizer templates."""

    model_yaml = parse_yaml_file(linkml)

    model = dict_to_schema(model_yaml)

    model_sv = s2sv(model)

    m_classes = model_sv.all_classes()

    if classname not in m_classes:
        print(f"no {classname} class in {linkml}")
        exit()
    else:
        selected_induced = model_sv.class_induced_slots(classname)
        # we are currently saving/expecting DH sections as slot categories
        for one_induced in selected_induced:
            oia = one_induced.annotations
            if 'Category' in oia:
                sect_val = oia['Category'].value
                sect_set.add(sect_val)
        category_list = list(sect_set)
        # alphabetize or otherwise order?
        # what about items for which no category was asserted?
        # iot_to_linkml may be discarding "required" category assertions
        category_list.sort()
        for one_cat in category_list:
            current_row = blank_row.copy()
            current_row['label'] = one_cat
            row_list.append(current_row)
        current_row = blank_row.copy()
        current_row['label'] = default_sect_val
        row_list.append(current_row)

        for one_induced in selected_induced:
            oia = one_induced.annotations
            sect_val = default_sect_val
            if 'Category' in oia:
                sect_val = oia['Category'].value
            current_row = blank_row.copy()
            current_row['Ontology ID'] = one_induced.slot_uri
            current_row['parent class'] = sect_val
            current_row['label'] = one_induced.name
            # expand this!
            # 'xs:token', 'xs:unique', 'xs:date', 'select', 'multiple', 'xs:nonNegativeInteger', 'xs:decimal'
            current_row['datatype'] = 'xs:token'
            # source
            # data status
            if one_induced.required == True:
                current_row['requirement'] = "required"
            if one_induced.recommended == True:
                current_row['requirement'] = "recommended"
            # min value
            # max value
            # capitalize
            # pattern
            current_row['description'] = one_induced.description

            comments_list = one_induced.comments
            comments_string = "|".join(comments_list)
            current_row['guidance'] = comments_string

            current_examples = one_induced.examples
            examples_list = []
            for one_example in current_examples:
                examples_list.append(one_example.value)
            examples_string = "|".join(examples_list)
            current_row['examples'] = examples_string

            row_list.append(current_row)

        dh_frame = pd.DataFrame(row_list)
        # print(dh_frame)
        dh_frame.to_csv(dh, sep="\t", index=False)


if __name__ == '__main__':
    l2dh_cli()
