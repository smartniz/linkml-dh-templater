import click
import linkml.utils.rawloader as rl
import pandas as pd
import yaml
from linkml_runtime.utils.schemaview import SchemaView

dh_cols = [
    'Ontology ID', 'parent class', 'label', 'datatype', 'source', 'data status', 'requirement', 'min value',
    'max value', 'capitalize', 'pattern', 'description', 'guidance', 'examples']

## ALL enums from IoT, with no regard to package:
# investigation_type	growth_facil	store_cond	samp_store_temp	plant_struc	growth_medium	biol_stat
# biotic_relationship	cur_land_use	drainage_class	fao_class	growth_habit	horizon	oxy_stat_samp
# plant_sex	profile_position	samp_capt_status	samp_dis_stage	sediment_type	tidal_stage	tillage	trophic_level

# default value is None
# would DataHarmonizer prefer something else?
blank_row = dict.fromkeys(dh_cols)

row_list = []
enum_list = []
sect_set = set()

default_sect_val = 'other'


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
@click.option('-s', '--sectord',
              help="""Section ordering. Use as many times as necessary. 
              Unmentioned sections in the LinkML will be added to the end in alphabetical order""",
              required=False, multiple=True)
def l2dh_cli(linkml, classname, dh, sectord):
    """CLI wrapper for converting LinkML to DataHarmonizer templates."""

    model_yaml = parse_yaml_file(linkml)

    model = dict_to_schema(model_yaml)

    model_sv = s2sv(model)

    m_classes = model_sv.all_classes()

    m_enums = model_sv.all_enums()
    m_enum_names = list(m_enums.keys())
    # m_enum_names.sort()
    # print(m_enum_names)

    if classname not in m_classes:
        print(f"no {classname} class in {linkml}")
        exit()
    else:
        selected_induced = model_sv.class_induced_slots(classname)
        # # we are currently saving/expecting DH sections as slot categories
        # # and is_a
        for one_induced in selected_induced:
            if one_induced.is_a != "" and one_induced.is_a is not None:
                sect_set.add(one_induced.is_a)
            else:
                sect_set.add(default_sect_val)
        category_list = list(sect_set)
        # alphabetize or otherwise order?
        # what about items for which no category was asserted?
        # iot_to_linkml may be discarding "required" category assertions
        # category_list.sort()

        sectord = list(sectord)
        print(f"You entered the sections in this order:              {sectord}")
        print(f"The following sections were deduced from your model: {category_list}")
        linkml_only_sections = list(set(category_list) - set(sectord))
        linkml_only_sections.sort()
        print(f"These sections were exclusively found in your model: {linkml_only_sections}")
        sectord_only_sections = list(set(sectord) - set(category_list))
        sectord_only_sections.sort()
        print(f"These sections could not be deduced from your model: {sectord_only_sections}")
        final_sectord = [keeper for keeper in sectord if keeper not in sectord_only_sections]
        final_sectord = final_sectord + linkml_only_sections
        print(f"Final section order:                                 {final_sectord}")

        for one_cat in final_sectord:
            current_row = blank_row.copy()
            current_row['label'] = one_cat
            row_list.append(current_row)

        for one_induced in selected_induced:
            oia = one_induced.annotations
            # sect_val = default_sect_val
            # if 'Category' in oia:
            #     sect_val = oia['Category'].value
            current_row = blank_row.copy()
            current_row['Ontology ID'] = one_induced.slot_uri
            if one_induced.is_a != "" and one_induced.is_a is not None:
                current_row['parent class'] = one_induced.is_a
            else:
                current_row['parent class'] = default_sect_val
            current_row['label'] = one_induced.title

            # expand this!
            # 'xs:token', 'xs:unique', 'xs:date', 'select', 'multiple', 'xs:nonNegativeInteger', 'xs:decimal'
            current_row['datatype'] = 'xs:token'
            if one_induced.identifier:
                current_row['datatype'] = 'xs:unique'
            # if 'unique_id' in oia and oia['unique_id']:
            #     pass
            if one_induced.range == "date":
                current_row['datatype'] = 'xs:date'
            if one_induced.range == "double":
                current_row['datatype'] = 'xs:decimal'

            if one_induced.range in m_enum_names:
                # when could it be multiple?
                current_row['datatype'] = 'select'
                pv_names = list(model.enums[one_induced.range].permissible_values.keys())
                pv_names.sort()
                for current_name in pv_names:
                    pv_row = blank_row.copy()
                    pv_row["parent class"] = one_induced.title
                    pv_row["label"] = current_name
                    enum_list.append(pv_row)

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
        enum_frame = pd.DataFrame(enum_list)
        dh_frame = dh_frame.append(enum_frame)
        dh_frame.to_csv(dh, sep="\t", index=False)


if __name__ == '__main__':
    l2dh_cli()
