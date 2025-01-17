from __future__ import absolute_import
from changes.models.latest_green_build import LatestGreenBuild

from base64 import b64encode
from loremipsum import get_paragraphs, get_sentences
from uuid import uuid4

from changes.config import db
from changes.models import (
    Repository, Job, JobPlan, Project, Revision, Change, Author,
    Patch, Plan, Step, Build, Source, Node, JobPhase, JobStep, Task,
    Artifact, TestCase, LogChunk, LogSource, Cluster, ClusterNode,
    RepositoryStatus, User, ItemOption, Command, Snapshot, SnapshotImage,
    CachedSnapshotImage, PlanStatus, AdminMessage, PhabricatorDiff
)
from changes.utils.slugs import slugify

__all__ = ('Fixtures', 'SAMPLE_COVERAGE', 'SAMPLE_DIFF', 'SAMPLE_XUNIT',
           'SAMPLE_XUNIT_DOUBLE_CASES',
           'SAMPLE_XUNIT_TESTARTIFACTS')


SAMPLE_COVERAGE = """<?xml version="1.0" ?>
<!DOCTYPE coverage
  SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
<coverage branch-rate="0" line-rate="0.4483" timestamp="1375818307337" version="3.6">
    <!-- Generated by coverage.py: http://nedbatchelder.com/code/coverage -->
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.4483" name="">
            <classes>
                <class branch-rate="0" complexity="0" filename="setup.py" line-rate="0" name="setup">
                    <methods/>
                    <lines>
                        <line hits="0" number="2"/>
                        <line hits="0" number="12"/>
                        <line hits="1" number="13"/>
                        <line hits="1" number="14"/>
                        <line hits="0" number="16"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="src/pytest_phabricator/plugin.py" line-rate="0.1875" name="src/pytest_phabricator/plugin">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                        <line hits="1" number="2"/>
                        <line hits="1" number="3"/>
                        <line hits="0" number="7"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>"""

with open('sample.diff', 'r') as f:
    SAMPLE_DIFF = f.read()

SAMPLE_XUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
    <testcase classname="" name="tests.test_report" time="0">
        <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock</failure>
    </testcase>
    <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.00165796279907" rerun="1"/>
</testsuite>"""

SAMPLE_XUNIT_DOUBLE_CASES = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="2" name="pytest" skips="0" tests="2" time="0.019">
  <testcase classname="test_simple.SampleTest" name="test_falsehood" time="0.25">
    <failure message="test failure">test_simple.py:8: in test_falsehood
    assert False
E   AssertionError: assert False</failure>
  </testcase>
  <testcase classname="test_simple.SampleTest" name="test_falsehood" time="0.50">
    <error message="test setup failure">test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero</error>
  </testcase>
  <testcase classname="test_simple.SampleTest" name="test_truth" time="1.25">
    <failure message="test failure">test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero</failure>
  </testcase>
</testsuite>"""

SAMPLE_XUNIT_TESTARTIFACTS = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
    <testcase classname="" name="tests.test_report" time="0">
        <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock</failure>
        <test-artifacts>
            <artifact name="sample_name.txt" type="text" base64="%s"/>
        </test-artifacts>
    </testcase>
    <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.00165796279907" rerun="1"/>
</testsuite>""" % b64encode('sample_content')


class Fixtures(object):
    def create_repo(self, **kwargs):
        kwargs.setdefault('url', 'http://example.com/{0}'.format(uuid4().hex))
        kwargs.setdefault('status', RepositoryStatus.active)

        repo = Repository(**kwargs)
        db.session.add(repo)
        db.session.commit()

        return repo

    def create_node(self, cluster=None, **kwargs):
        kwargs.setdefault('label', uuid4().hex)

        node = Node(**kwargs)
        db.session.add(node)

        if cluster:
            db.session.add(ClusterNode(cluster=cluster, node=node))

        db.session.commit()

        return node

    def create_cluster(self, **kwargs):
        kwargs.setdefault('label', uuid4().hex)

        cluster = Cluster(**kwargs)
        db.session.add(cluster)
        db.session.commit()

        return cluster

    def create_project(self, **kwargs):
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id
        kwargs.setdefault('name', uuid4().hex)
        kwargs.setdefault('slug', kwargs['name'])

        project = Project(**kwargs)
        db.session.add(project)
        db.session.commit()

        return project

    def create_change(self, project, **kwargs):
        kwargs.setdefault('label', 'Sample')

        change = Change(
            hash=uuid4().hex,
            repository=project.repository,
            project=project,
            **kwargs
        )
        db.session.add(change)
        db.session.commit()

        return change

    def create_test(self, job, **kwargs):
        kwargs.setdefault('name', uuid4().hex)

        case = TestCase(
            job=job,
            project=job.project,
            project_id=job.project_id,
            job_id=job.id,
            **kwargs
        )
        db.session.add(case)
        db.session.commit()

        return case

    def create_job(self, build, **kwargs):
        project = build.project

        kwargs.setdefault('label', build.label)
        kwargs.setdefault('status', build.status)
        kwargs.setdefault('result', build.result)
        kwargs.setdefault('duration', build.duration)
        kwargs.setdefault('date_started', build.date_started)
        kwargs.setdefault('date_finished', build.date_finished)
        kwargs.setdefault('source', build.source)

        if kwargs.get('change', False) is False:
            kwargs['change'] = self.create_change(project)

        job = Job(
            build=build,
            build_id=build.id,
            project=project,
            project_id=project.id,
            **kwargs
        )
        db.session.add(job)
        db.session.commit()

        return job

    def create_job_plan(self, job, plan):
        jobplan = JobPlan.build_jobplan(plan, job)
        db.session.add(jobplan)
        db.session.commit()

        return jobplan

    def create_source(self, project, **kwargs):
        if 'revision_sha' not in kwargs:
            revision = self.create_revision(repository=project.repository)
            kwargs['revision_sha'] = revision.sha
        if 'data' not in kwargs:
            data = {
                'phabricator.revisionID': '1234',
                'phabricator.revisionURL': 'https://tails.corp.dropbox.com/D1234'
            }
            kwargs['data'] = data

        source = Source(
            repository_id=project.repository_id,
            **kwargs
        )
        db.session.add(source)
        db.session.commit()

        return source

    def create_diff(self, diff_id, **kwargs):
        diff = PhabricatorDiff(
            diff_id=diff_id,
            **kwargs
        )
        db.session.add(diff)
        db.session.commit()
        return diff

    def create_build(self, project, **kwargs):
        if 'source' not in kwargs:
            kwargs['source'] = self.create_source(project)
        if 'collection_id' not in kwargs:
            kwargs['collection_id'] = uuid4()

        kwargs['source_id'] = kwargs['source'].id

        kwargs.setdefault('label', 'Sample')

        build = Build(
            project_id=project.id,
            project=project,
            **kwargs
        )
        db.session.add(build)
        db.session.commit()

        return build

    def create_patch(self, **kwargs):
        kwargs.setdefault('diff', SAMPLE_DIFF)
        kwargs.setdefault('parent_revision_sha', uuid4().hex)
        if not kwargs.get('repository_id'):
            if not kwargs.get('repository'):
                kwargs['repository'] = self.create_repo()
            kwargs['repository_id'] = kwargs['repository'].id

        patch = Patch(
            **kwargs
        )
        db.session.add(patch)
        db.session.commit()

        return patch

    def create_revision(self, **kwargs):
        kwargs.setdefault('sha', uuid4().hex)
        if not kwargs.get('repository_id'):
            if not kwargs.get('repository'):
                kwargs['repository'] = self.create_repo()
            kwargs['repository_id'] = kwargs['repository'].id

        if 'author' not in kwargs:
            kwargs['author'] = self.create_author()

        if kwargs.get('author'):
            kwargs['author_id'] = kwargs['author'].id

        if not kwargs.get('message'):
            message = get_sentences(1)[0][:128] + '\n'
            message += '\n\n'.join(get_paragraphs(2))
            kwargs['message'] = message

        revision = Revision(**kwargs)
        db.session.add(revision)
        db.session.commit()

        return revision

    def create_author(self, email=None, **kwargs):
        if not kwargs.get('name'):
            kwargs['name'] = ' '.join(get_sentences(1)[0].split(' ')[0:2])

        if not email:
            email = '{0}-{1}@example.com'.format(
                slugify(kwargs['name']), uuid4().hex)

        kwargs.setdefault('name', 'Test Case')

        author = Author(email=email, **kwargs)
        db.session.add(author)
        db.session.commit()

        return author

    def create_plan(self, project, **kwargs):
        kwargs.setdefault('label', 'test')
        kwargs.setdefault('status', PlanStatus.active)

        plan = Plan(project=project, **kwargs)
        db.session.add(plan)
        db.session.commit()

        return plan

    def create_step(self, plan, **kwargs):
        kwargs.setdefault('implementation', 'changes.buildsteps.dummy.DummyBuildStep')
        kwargs.setdefault('order', 0)

        step = Step(plan=plan, **kwargs)
        db.session.add(step)
        db.session.commit()

        return step

    def create_jobphase(self, job, **kwargs):
        kwargs.setdefault('label', 'test')
        kwargs.setdefault('result', job.result)
        kwargs.setdefault('status', job.status)

        phase = JobPhase(
            job=job,
            project=job.project,
            **kwargs
        )
        db.session.add(phase)
        db.session.commit()

        return phase

    def create_jobstep(self, phase, **kwargs):
        kwargs.setdefault('label', phase.label)
        kwargs.setdefault('result', phase.result)
        kwargs.setdefault('status', phase.status)

        step = JobStep(
            job=phase.job,
            project=phase.project,
            phase=phase,
            **kwargs
        )
        db.session.add(step)
        db.session.commit()

        return step

    def create_command(self, jobstep, **kwargs):
        kwargs.setdefault('label', 'a command')
        kwargs.setdefault('script', 'echo 1')

        command = Command(
            jobstep=jobstep,
            **kwargs
        )
        db.session.add(command)
        db.session.commit()

        return command

    def create_task(self, **kwargs):
        kwargs.setdefault('task_id', uuid4())

        task = Task(**kwargs)
        db.session.add(task)
        db.session.commit()

        return task

    def create_artifact(self, step, name, **kwargs):
        artifact = Artifact(
            step=step,
            project=step.project,
            job=step.job,
            name=name,
            **kwargs
        )
        db.session.add(artifact)
        db.session.commit()

        return artifact

    def create_logsource(self, step=None, **kwargs):
        if step:
            kwargs['job'] = step.job
        kwargs['project'] = kwargs['job'].project

        logsource = LogSource(
            step=step,
            **kwargs
        )
        db.session.add(logsource)
        db.session.commit()

        return logsource

    def create_logchunk(self, source, text=None, **kwargs):
        # TODO(dcramer): we should default offset to previosu entry in LogSource
        kwargs.setdefault('offset', 0)
        kwargs['job'] = source.job
        kwargs['project'] = source.project

        if text is None:
            text = '\n'.join(get_sentences(4))

        logchunk = LogChunk(
            source=source,
            text=text,
            size=len(text),
            **kwargs
        )
        db.session.add(logchunk)
        db.session.commit()

        return logchunk

    def create_user(self, email, **kwargs):
        user = User(email=email, **kwargs)
        db.session.add(user)
        db.session.commit()
        return user

    def create_option(self, **kwargs):
        option = ItemOption(**kwargs)
        db.session.add(option)
        db.session.commit()
        return option

    def create_latest_green_build(self, **kwargs):
        if not kwargs.get('project'):
            kwargs['project'] = self.create_repo()
        kwargs['project_id'] = kwargs['project'].id

        latest_green_build = LatestGreenBuild(**kwargs)
        db.session.add(latest_green_build)
        db.session.commit()

        return latest_green_build

    def create_snapshot(self, project, **kwargs):
        snapshot = Snapshot(
            project_id=project.id,
            project=project,
            **kwargs
        )
        db.session.add(snapshot)
        db.session.commit()

        return snapshot

    def create_snapshot_image(self, snapshot, plan, **kwargs):
        image = SnapshotImage(
            snapshot=snapshot,
            plan=plan,
            **kwargs
        )
        db.session.add(image)
        db.session.commit()
        return image

    def create_cached_snapshot_image(self, snapshot_image, **kwargs):
        cached_snapshot_image = CachedSnapshotImage(
            id=snapshot_image.id,
            **kwargs)
        db.session.add(cached_snapshot_image)
        db.session.commit()
        return cached_snapshot_image

    def create_adminmessage(self, **kwargs):
        message = AdminMessage(
            **kwargs
        )
        db.session.add(message)
        db.session.commit()
        return message
