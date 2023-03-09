
import itertools
import pathlib

import pandas as pd
import numpy as np
import modelx as mx
import pytest
from modelx.serialize import ziputil


# Modified from the sample code on
# https://pandas.pydata.org/docs/user_guide/advanced.html

cols = [
    ["bar", "bar", "baz", "baz", "foo", "foo", "qux", "qux"],
    ["one", "two", "one", "two", "one", "two", "one", "two"]
]
cols = list(zip(*cols))
cols = pd.MultiIndex.from_tuples(cols, names=["first", "second"])
idx = pd.MultiIndex.from_product([["A", "B"], ["c", "d", "e"]])
idx.name = 'Idx'

S_IDX1 = pd.Series(np.random.randn(8), index=range(8))
S_IDX1.index.name = "Idx"
S_IDX2 = pd.Series(np.random.randn(8), index=cols)
DF_COL2_IDX2 = pd.DataFrame(np.random.randn(6, 8), index=idx, columns=cols)

params = [[p1, *p2, p3, p4] for p1, p2, p3, p4 in
          itertools.product(
              [S_IDX1, S_IDX2, DF_COL2_IDX2],
              [("model", True), ("space", False)],
              ("write", "zip", "backup"),
              ("excel", "csv")
            )
          ]


@pytest.mark.parametrize(
    "pdobj, pstr, is_relative, save_meth, filetype",
    params)
def test_new_pandas(
        tmp_path, pdobj, pstr, is_relative, save_meth, filetype):

    m = mx.new_model()
    parent = m if pstr == "model" else m.new_space()
    parent_name = parent.name

    file_path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    parent.new_pandas(name="pdref", path=file_path,
                 data=pdobj, file_type=filetype)

    # For checking preserved object identity
    parent.nestedpd = [pdobj]

    for nth in "12":
        model_name = f"model{nth}"
        model_loc = tmp_path / model_name
        file_loc = (model_loc / file_path) if is_relative else file_path

        # Save, close and restore
        if save_meth == "backup":
            getattr(m, save_meth)(model_loc)
            m.close()
            m = mx.restore_model(model_loc)
        else:
            getattr(m, save_meth)(model_loc)
            m.close()
            assert ziputil.exists(file_loc)
            m = mx.read_model(model_loc)

        parent = m if pstr == "model" else m.spaces[parent_name]

        m._impl.system._check_sanity(check_members=False)
        m._impl._check_sanity()

        if isinstance(pdobj, pd.DataFrame):
            pd.testing.assert_frame_equal(parent.pdref, pdobj)
        elif isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(parent.pdref, pdobj)

        # Check object identity preservation
        assert parent.pdref is parent.nestedpd[0]

        pd.testing.assert_index_equal(parent.pdref.index, pdobj.index)
            # TODO: assert parent.pdref.index.name == pdobj.index.name

    m.close()


params2 = zip([S_IDX1, S_IDX2, DF_COL2_IDX2], ["B2:B9", "C2:C9", "C4:J9"])


@pytest.mark.parametrize("pdobj, range_", params2)
def test_new_pandas_change_excel(tmp_path, pdobj, range_):

    p = mx.new_model().new_space("SpaceA")

    path = "files/testpandas.xlsx"
    p.new_pandas(name="pdref", path=path, data=pdobj, file_type="excel")

    p.model.write(tmp_path / "model")
    p.model.close()

    import openpyxl as pyxl

    wb = pyxl.load_workbook(tmp_path / "model" / path)
    ws = wb.worksheets[0]

    for row in ws[range_]:
        for cel in row:
            cel.value += 1

    wb.save(tmp_path / "model" / path)

    m2 = mx.read_model(tmp_path / "model")
    p2 = m2.spaces["SpaceA"]

    if isinstance(pdobj, pd.DataFrame):
        pd.testing.assert_frame_equal(p2.pdref, pdobj + 1)
    elif isinstance(pdobj, pd.Series):
        pd.testing.assert_series_equal(p2.pdref, pdobj + 1)

    pd.testing.assert_index_equal(p2.pdref.index, pdobj.index)
    # TODO: assert p2.pdref.index.name == pdobj.index.name

    m2.close()


params_mult_sheets = [
    [*p1, p2] for p1, p2 in
          itertools.product(
              [("model", True), ("space", False)],
              ("write", "zip"),
            )
]


def assert_pandas_refs(parent):

    pd.testing.assert_series_equal(parent.s1, S_IDX1)
    pd.testing.assert_series_equal(parent.s2, S_IDX2)
    pd.testing.assert_frame_equal(parent.df1, DF_COL2_IDX2)

    pd.testing.assert_index_equal(parent.s1.index, S_IDX1.index)
    pd.testing.assert_index_equal(parent.s2.index, S_IDX2.index)
    pd.testing.assert_index_equal(parent.df1.index, DF_COL2_IDX2.index)


@pytest.mark.parametrize(
    "pstr, is_relative, save_meth", params_mult_sheets)
def test_new_pandas_mult_sheets(
        tmp_path, pstr, is_relative, save_meth):
    """Test writing to multiple sheets in an Excel file"""

    m = mx.new_model()
    parent = m if pstr == "model" else m.new_space()
    parent_name = parent.name

    file_path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    for obj, name in zip((S_IDX1, S_IDX2, DF_COL2_IDX2), ("s1", "s2", "df1")):

        parent.new_pandas(
            name=name, path=file_path,
            data=obj, file_type="excel", sheet=name)

    for nth in "12":
        model_name = f"model{nth}"
        model_loc = tmp_path / model_name
        file_loc = (model_loc / file_path) if is_relative else file_path

        # Save, close and restore
        getattr(m, save_meth)(model_loc)
        m.close()
        assert ziputil.exists(file_loc)
        m = mx.read_model(model_loc)

        parent = m if pstr == "model" else m.spaces[parent_name]

        m._impl.system._check_sanity(check_members=False)
        m._impl._check_sanity()

        assert_pandas_refs(parent)

    m.close()


@pytest.mark.parametrize("pstr, is_relative, save_meth", params_mult_sheets)
def test_update_path(tmp_path, pstr, is_relative, save_meth):
    """Test if updating the path of SharedIO"""
    m = mx.new_model()
    parent = m if pstr == "model" else m.new_space()
    parent_name = parent.name

    file_path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    for obj, name in zip((S_IDX1, S_IDX2, DF_COL2_IDX2), ("s1", "s2", "df1")):

        parent.new_pandas(
            name=name, path=file_path,
            data=obj, file_type="excel", sheet=name)

    for nth in "12":
        model_name = f"model{nth}"
        model_loc = tmp_path / model_name

        # --- Update the path of SharedIO ---
        new_file_path = (
            f"files/testpandas{nth}.xlsx"
            if is_relative
            else tmp_path / f"testpandas{nth}.xlsx"
        )

        m.get_spec(parent.s1).path = new_file_path
        file_loc = (model_loc / new_file_path) if is_relative else new_file_path

        assert m.get_spec(parent.s1).path == pathlib.Path(new_file_path)
        assert m.get_spec(parent.s2).path == pathlib.Path(new_file_path)
        assert m.get_spec(parent.df1).path == pathlib.Path(new_file_path)
        assert m.iospecs[0].path == pathlib.Path(new_file_path)
        # ------------------------------------

        # Save, close and restore
        getattr(m, save_meth)(model_loc)
        m.close()
        assert ziputil.exists(file_loc)
        m = mx.read_model(model_loc)

        parent = m if pstr == "model" else m.spaces[parent_name]

        m._impl.system._check_sanity(check_members=False)
        m._impl._check_sanity()

        assert_pandas_refs(parent)

    m.close()


@pytest.mark.parametrize("pstr, is_relative, save_meth", params_mult_sheets)
def test_update_sheet(tmp_path, pstr, is_relative, save_meth):
    """Test if updating the path of SharedIO"""
    m = mx.new_model()
    parent = m if pstr == "model" else m.new_space()
    parent_name = parent.name

    file_path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    for obj, name in zip((S_IDX1, S_IDX2, DF_COL2_IDX2), ("s1", "s2", "df1")):
        parent.new_pandas(
            name=name, path=file_path,
            data=obj, file_type="excel", sheet=name)

    for nth in "12":
        model_name = f"model{nth}"
        model_loc = tmp_path / model_name
        file_loc = (model_loc / file_path) if is_relative else file_path

        old_sheet = []
        for obj in (parent.s1, parent.s2, parent.df1):
            old_sheet.append(m.get_spec(obj).sheet)
            m.get_spec(obj).sheet = old_sheet[-1] + nth
            assert m.get_spec(obj).sheet == old_sheet[-1] + nth

        # Save, close and restore
        getattr(m, save_meth)(model_loc)
        m.close()
        assert ziputil.exists(file_loc)
        m = mx.read_model(model_loc)
        parent = m if pstr == "model" else m.spaces[parent_name]

        for obj in (parent.s1, parent.s2, parent.df1):
            assert m.get_spec(obj).sheet == old_sheet.pop(0) + nth

        m._impl.system._check_sanity(check_members=False)
        m._impl._check_sanity()

        assert_pandas_refs(parent)

    m.close()


params_update = [
    [*p1, p2, p3] for p1, p2, p3 in
          itertools.product(
              [("model", True), ("space", False)],
              ("write", "zip"),
              ("excel", "csv")
          )]


@pytest.mark.parametrize(
    "pstr, is_relative, save_meth, filetype", params_update)
def test_update_pandas(
        tmp_path, pstr, is_relative, save_meth, filetype):

    m = mx.new_model()
    parent = m if pstr == "model" else m.new_space()
    parent_name = parent.name

    file_path = "files/testpandas.xlsx" if is_relative else (
            tmp_path / "testpandas.xlsx")

    parent.new_pandas(name="pdref", path=file_path,
                      data=S_IDX1, file_type=filetype)
    pd.testing.assert_series_equal(parent.pdref, S_IDX1)

    for nth in "12":

        pdobj = S_IDX2 if nth == "1" else DF_COL2_IDX2

        m.update_pandas(parent.pdref, pdobj)

        if isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(parent.pdref, pdobj)
        else:
            pd.testing.assert_frame_equal(parent.pdref, pdobj)

        model_name = f"model{nth}"
        model_loc = tmp_path / model_name
        file_loc = (model_loc / file_path) if is_relative else file_path

        # Save, close and restore
        getattr(m, save_meth)(model_loc)
        m.close()

        assert ziputil.exists(file_loc)
        m = mx.read_model(model_loc)

        parent = m if pstr == "model" else m.spaces[parent_name]

        m._impl.system._check_sanity(check_members=False)
        m._impl._check_sanity()

        if isinstance(pdobj, pd.Series):
            pd.testing.assert_series_equal(parent.pdref, pdobj)
        else:
            pd.testing.assert_frame_equal(parent.pdref, pdobj)

    m.close()


def test_update_pandas_no_spec():
    """
        m---SpaceA---SpaceB
    """
    m = mx.new_model()
    SpaceA = m.new_space('SpaceA')
    SpaceB = SpaceA.new_space('SpaceB')

    m.s1 = S_IDX1
    SpaceA.s2 = S_IDX1
    SpaceB.s3 = S_IDX1

    assert m.s1 is S_IDX1
    assert SpaceA.s2 is S_IDX1
    assert SpaceB.s3 is S_IDX1

    m.update_pandas(S_IDX1, S_IDX2)

    assert m.s1 is S_IDX2
    assert SpaceA.s2 is S_IDX2
    assert SpaceB.s3 is S_IDX2

    m.close()


@pytest.mark.parametrize("parent_type, has_spec", [["model", "space"], [True, False]])
def test_update_pandas_no_new_value(parent_type, has_spec):

    m = mx.new_model()
    s_base = m.new_space()
    s_sub = m.new_space(bases=s_base)

    @mx.defcells(space=s_base)
    def foo():
        return x['col1'][0]

    parent = m if parent_type == "model" else s_base

    df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})

    if has_spec:
        parent.new_pandas('x', 'df.xlsx', df, 'excel')
        spec = parent.get_spec(df)
    else:
        parent.x = df

    assert s_base.foo() == 1
    assert s_sub.foo() == 1

    df['col1'][0] = 5
    m.update_pandas(df)

    assert s_base.foo() == 5
    assert s_sub.foo() == 5

    if has_spec:
        assert m.get_spec(df) is spec


@pytest.mark.parametrize("parent_type", ["model", "space"])
def test_del_val_with_spec_by_change_ref(parent_type):

    m = mx.new_model()
    s = m.new_space()
    parent = m if parent_type == "model" else s

    df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
    df2 = pd.DataFrame({'col3': [5, 6], 'col4': [7, 8]})

    parent.new_pandas('foo', 'foo.xlsx', df, 'excel')

    parent.foo = df2

    assert parent.foo is df2
    assert not m.iospecs

    if parent_type == "model":
        parent._impl._check_sanity()

    m.close()