"""Publication verification fails closed before any artifact installation."""
import copy
import importlib.util
from email.parser import Parser
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pypi_release',ROOT/'scripts/iteration/pypi_release.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from validate_full_package import artifact_kind,canonical_project_name,require_metadata_identity


class PublishedReleaseChecks(unittest.TestCase):
    def setUp(self):
        self.expected={'py_elk-0.1.0-py3-none-any.whl':'1'*64,'py_elk-0.1.0.tar.gz':'2'*64}
        self.index={'info':{'name':'py-elk','version':'0.1.0','requires_python':'>=3.11',
                            'requires_dist':['build==1.6.1; extra == "dev"']},
                    'urls':[{'filename':name,'digests':{'sha256':sha},'yanked':False,
                             'packagetype':'bdist_wheel'if name.endswith('.whl')else'sdist',
                             'url':'https://files.pythonhosted.org/packages/'+name}
                            for name,sha in self.expected.items()]}

    def test_exact_public_file_hashes_and_metadata_are_required(self):
        self.assertEqual(set(module.verify_index(self.index,'0.1.0',self.expected,project='py-elk')),set(self.expected))
        mutations=[lambda v:v['urls'][0]['digests'].__setitem__('sha256','0'*64),
                   lambda v:v['info'].__setitem__('version','0.0.1a0'),
                   lambda v:v['info'].__setitem__('requires_dist',['elkjs-runtime']),
                   lambda v:v['urls'].append(copy.deepcopy(v['urls'][0])),
                   lambda v:v['urls'][0].__setitem__('url','https://example.invalid/unreviewed.whl'),
                   lambda v:v['urls'][0].__setitem__('yanked',True),
                   lambda v:v['urls'][0].__setitem__('packagetype','sdist'),
                   lambda v:v['info'].__setitem__('name','wrong-project'),
                   lambda v:v['info'].__setitem__('name',None)]
        for mutate in mutations:
            value=copy.deepcopy(self.index);mutate(value)
            with self.subTest(mutation=repr(mutate)),self.assertRaises(ValueError):
                module.verify_index(value,'0.1.0',self.expected,project='py-elk')

    def test_plan_performs_no_network_or_product_execution(self):
        plan=module.plan('0.1.0',project='py-elk')
        self.assertFalse(plan['publishes'])
        self.assertEqual((plan['networkRequestsExecuted'],plan['layoutExecutions']),(0,0))
        self.assertEqual(plan['index'],'https://pypi.org/pypi/py-elk/0.1.0/json')

    def test_new_project_and_pyproject_default_use_normalized_names(self):
        expected={name.replace('py_elk','py_visactor_elk'):sha for name,sha in self.expected.items()}
        index=copy.deepcopy(self.index)
        index['info']['name']='PY.VisActor_Elk'
        for row in index['urls']:
            row['filename']=row['filename'].replace('py_elk','py_visactor_elk')
            row['url']=row['url'].replace('py_elk','py_visactor_elk')
        with patch.object(module,'project_metadata',return_value={'name':'py-visactor-elk'}):
            self.assertEqual(set(module.verify_index(index,'0.1.0',expected)),set(expected))
            plan=module.plan('0.1.0')
        self.assertEqual(plan['index'],'https://pypi.org/pypi/py-visactor-elk/0.1.0/json')
        self.assertEqual(plan['importPackage'],'pyelk')
        with self.assertRaises(ValueError):
            module.verify_index(self.index,'0.1.0',self.expected,project='py-visactor-elk')

    def test_archive_identity_and_metadata_reject_wrong_name_or_type(self):
        self.assertEqual(artifact_kind('py_visactor_elk-0.1.0-py3-none-any.whl','py-visactor-elk','0.1.0'),'bdist_wheel')
        self.assertEqual(artifact_kind('py_visactor_elk-0.1.0.tar.gz','py-visactor-elk','0.1.0'),'sdist')
        invalid=['py_elk-0.1.0-py3-none-any.whl','py-visactor-elk-0.1.0.tar.gz',
                 'py_visactor_elk-0.1.0.zip','../py_visactor_elk-0.1.0.tar.gz',
                 'py_visactor_elk-0.2.0-py3-none-any.whl',None,False]
        for filename in invalid:
            with self.subTest(filename=filename),self.assertRaises(ValueError):
                artifact_kind(filename,'py-visactor-elk','0.1.0')
        metadata=Parser().parsestr('Name: py-visactor-elk\nVersion: 0.1.0\n')
        require_metadata_identity(metadata,'py-visactor-elk','0.1.0')
        with self.assertRaises(ValueError):
            require_metadata_identity(metadata,'py-elk','0.1.0')
        for name in (None,False,7,'../bad','', 'ends-'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                canonical_project_name(name)


if __name__=='__main__':unittest.main()
