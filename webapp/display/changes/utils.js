import React from 'react';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/* A variety of changes-specific functions:
 * 1. Some formatters, e.g. creating a shorter name from a repository url
 *
 * 2. Things that seemed too small to be worth making into tags, e.g. taking an
 * author object and rendering a link for their username
 *
 * 3. TODO: links to other pages
 */
var DisplayUtils = {

  // If I want to be able to customize these (e.g. add a css class), they
  // should be tags instead

  authorLink: function(author) {
    if (!author) {
      return 'unknown';
    }
    var author_href = `/v2/author/${author.email}`;
    return <a href={author_href}>
      {utils.email_head(author.email)}
    </a>;
  },

  projectLink: function(project) {
    var href = `/v2/project/${project.slug}/`;
    return <a href={href}>{project.name}</a>;
  },


  // grabs the last path param or filename after : for a repo name
  // TODO: move out of this file
  getShortRepoName: function(repo_url) {
    return _.last(_.compact(repo_url.split(/:|\//)));
  },

  // takes a blob of text and wraps urls in anchor tags
  linkifyURLs: function(string, link_class = '') {
    var url_positions = [];
    URI.withinString(string, (url, start, end, source) => {
      url_positions.push([start, end]);
      return url;
    });

    var elements = [];

    // manual, sequential slicing
    var current_pos = 0;
    _.each(url_positions, pos => {
      var [start, end] = pos;
      elements.push(string.substring(current_pos, start));
      var uri = string.substring(start, end);
      elements.push(
        <a className={link_class} href={uri} target="_blank">
          {uri}
        </a>
      );
      current_pos = end;
    });
    elements.push(string.substring(current_pos));

    return elements;
  }
};

export default DisplayUtils;
