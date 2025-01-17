from __future__ import absolute_import, division, unicode_literals

import logging
import uuid

from flask_restful.reqparse import RequestParser

from sqlalchemy.orm import subqueryload_all
from changes.utils.diff_parser import DiffParser
from werkzeug.datastructures import FileStorage
from changes.api.base import APIView, error
from changes.api.build_index import (
    create_build, get_build_plans, identify_revision, MissingRevision
)
from changes.api.validators.author import AuthorValidator
from changes.config import db, statsreporter
from changes.db.utils import try_create
from changes.models import (
    ItemOption, Patch, PhabricatorDiff, Project, ProjectOption, ProjectOptionsHelper, ProjectStatus,
    Repository, RepositoryStatus, Source, ProjectConfigError,
)
from changes.utils.project_trigger import files_changed_should_trigger_project
from changes.vcs.base import InvalidDiffError


def get_repository_by_callsign(callsign):
    # It's possible to have multiple repositories with the same callsign due
    # to us not enforcing a unique constraint (via options). Given that it is
    # complex and shouldn't actually happen we make an assumption that there's
    # only a single repo
    item_id_list = db.session.query(ItemOption.item_id).filter(
        ItemOption.name == 'phabricator.callsign',
        ItemOption.value == callsign,
    )
    repo_list = list(Repository.query.filter(
        Repository.id.in_(item_id_list),
        Repository.status == RepositoryStatus.active,
    ))
    if len(repo_list) > 1:
        logging.warning('Multiple repositories found matching phabricator.callsign=%s', callsign)
    elif not repo_list:
        return None  # Match behavior of project and repository parameters
    return repo_list[0]


class PhabricatorNotifyDiffAPIView(APIView):
    parser = RequestParser()
    parser.add_argument('sha', type=str, required=True)
    parser.add_argument('author', type=AuthorValidator(), required=True)
    parser.add_argument('label', type=unicode, required=True)
    parser.add_argument('message', type=unicode, required=True)
    parser.add_argument('patch', type=FileStorage, dest='patch_file',
                        location='files', required=True)

    parser.add_argument('phabricator.callsign', type=get_repository_by_callsign,
                        required=True, dest='repository')
    parser.add_argument('phabricator.buildTargetPHID', required=False)
    parser.add_argument('phabricator.diffID', required=True)
    parser.add_argument('phabricator.revisionID', required=True)
    parser.add_argument('phabricator.revisionURL', required=True)

    def post(self):
        """
        Notify Changes of a newly created diff.

        Depending on system configuration, this may create 0 or more new builds,
        and the resulting response will be a list of those build objects.
        """
        args = self.parser.parse_args()

        repository = args.repository
        if not args.repository:
            return error("Repository not found")

        projects = list(Project.query.options(
            subqueryload_all('plans'),
        ).filter(
            Project.status == ProjectStatus.active,
            Project.repository_id == repository.id,
        ))

        # no projects bound to repository
        if not projects:
            return self.respond([])

        options = dict(
            db.session.query(
                ProjectOption.project_id, ProjectOption.value
            ).filter(
                ProjectOption.project_id.in_([p.id for p in projects]),
                ProjectOption.name.in_([
                    'phabricator.diff-trigger',
                ])
            )
        )

        projects = [
            p for p in projects
            if options.get(p.id, '1') == '1'
        ]

        if not projects:
            return self.respond([])

        statsreporter.stats().incr('diffs_posted_from_phabricator')

        label = args.label[:128]
        author = args.author
        message = args.message
        sha = args.sha
        target = 'D{}'.format(args['phabricator.revisionID'])

        try:
            identify_revision(repository, sha)
        except MissingRevision:
            # This may just be a broken request (which is why we respond with a 400) but
            # it also might indicate Phabricator and Changes being out of sync somehow,
            # so we err on the side of caution and log it as an error.
            logging.error("Diff %s was posted for an unknown revision (%s, %s)",
                          target, sha, repository.url)
            return error("Unable to find commit %s in %s." % (
                sha, repository.url), problems=['sha', 'repository'])

        source_data = {
            'phabricator.buildTargetPHID': args['phabricator.buildTargetPHID'],
            'phabricator.diffID': args['phabricator.diffID'],
            'phabricator.revisionID': args['phabricator.revisionID'],
            'phabricator.revisionURL': args['phabricator.revisionURL'],
        }

        patch = Patch(
            repository=repository,
            parent_revision_sha=sha,
            diff=''.join(args.patch_file),
        )
        db.session.add(patch)

        source = Source(
            patch=patch,
            repository=repository,
            revision_sha=sha,
            data=source_data,
        )
        db.session.add(source)

        phabricatordiff = try_create(PhabricatorDiff, {
            'diff_id': args['phabricator.diffID'],
            'revision_id': args['phabricator.revisionID'],
            'url': args['phabricator.revisionURL'],
            'source': source,
        })
        if phabricatordiff is None:
            logging.error("Diff %s, Revision %s already exists",
                          args['phabricator.diffID'], args['phabricator.revisionID'])
            return error("Diff already exists within Changes")

        project_options = ProjectOptionsHelper.get_options(projects, ['build.file-whitelist'])
        diff_parser = DiffParser(patch.diff)
        files_changed = diff_parser.get_changed_files()

        collection_id = uuid.uuid4()
        builds = []
        for project in projects:
            plan_list = get_build_plans(project)
            if not plan_list:
                logging.warning('No plans defined for project %s', project.slug)
                continue

            try:
                if not files_changed_should_trigger_project(files_changed, project, project_options[project.id], sha, diff=patch.diff):
                    logging.info('No changed files matched project trigger for project %s', project.slug)
                    continue
            except InvalidDiffError:
                # ok, the build will fail and the user will be notified
                pass
            except ProjectConfigError:
                logging.error('Project config for project %s is not in a valid format. Author is %s.', project.slug, author.name, exc_info=True)

            builds.append(create_build(
                project=project,
                collection_id=collection_id,
                sha=sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch=patch,
                tag="phabricator",
            ))
        # This is the counterpoint to the above 'diffs_posted_from_phabricator';
        # at this point we've successfully processed the diff, so comparing this
        # stat to the above should give us the phabricator diff failure rate.
        statsreporter.stats().incr('diffs_successfully_processed_from_phabricator')

        return self.respond(builds)
