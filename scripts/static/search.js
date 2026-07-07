(function () {
  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function hasCjk(text) {
    return /[\u3040-\u9fff\uff00-\uffef]/.test(text);
  }

  function substringSearch(query, docs) {
    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
      return [];
    }

    const results = [];
    docs.forEach(function (doc) {
      const title = doc.title_search || doc.title || "";
      const excerpt = doc.excerpt_search || doc.excerpt || "";
      const body = doc.body_search || doc.body || "";
      const topics = doc.topics_search || (doc.topics || []).join(" ");
      let score = 0;

      if (title.includes(normalizedQuery)) {
        score = 3;
      } else if (excerpt.includes(normalizedQuery)) {
        score = 2;
      } else if (topics.includes(normalizedQuery)) {
        score = 1.5;
      } else if (body.includes(normalizedQuery)) {
        score = 1;
      }

      if (score) {
        results.push({ ref: doc.id, score: score });
      }
    });

    results.sort(function (a, b) {
      return b.score - a.score;
    });
    return results;
  }

  function searchDocuments(query, docs, lunrIndex) {
    if (hasCjk(query)) {
      return substringSearch(query, docs);
    }

    try {
      const lunrMatches = lunrIndex.search(query);
      if (lunrMatches.length > 0) {
        return lunrMatches;
      }
    } catch (error) {
      // fall through to substring search
    }

    return substringSearch(query, docs);
  }

  function buildIndex(docs) {
    return lunr(function () {
      this.ref("id");
      this.field("title", { boost: 10 });
      this.field("topics", { boost: 5 });
      this.field("excerpt", { boost: 2 });
      this.field("body");

      docs.forEach(function (doc) {
        this.add({
          id: doc.id,
          title: doc.title || "",
          topics: Array.isArray(doc.topics) ? doc.topics.join(" ") : doc.topics || "",
          excerpt: doc.excerpt || "",
          body: doc.body || "",
        });
      }, this);
    });
  }

  function initSearch(options) {
    const input = document.getElementById(options.inputId);
    const status = document.getElementById(options.statusId);
    const results = document.getElementById(options.resultsId);
    if (!input || !status || !results) {
      return;
    }

    let documents = [];
    let index = null;

    function renderResults(matches) {
      results.innerHTML = "";

      if (!input.value.trim()) {
        status.textContent = "";
        return;
      }

      if (matches.length === 0) {
        status.textContent = "No results.";
        return;
      }

      status.textContent =
        matches.length === 1 ? "1 result" : matches.length + " results";

      matches.slice(0, options.limit || 20).forEach(function (match) {
        const doc = documents.find(function (item) {
          return item.id === match.ref;
        });
        if (!doc) {
          return;
        }

        const item = document.createElement("li");
        item.className = "search-result";

        const metaParts = [];
        if (doc.hub_title) {
          metaParts.push(doc.hub_title);
        } else if (doc.layer) {
          metaParts.push(doc.layer);
        } else if (doc.section) {
          metaParts.push(doc.section);
        }
        if (doc.backlink_count) {
          metaParts.push(
            doc.backlink_count === 1
              ? "1 backlink"
              : doc.backlink_count + " backlinks"
          );
        }
        if (doc.date) {
          metaParts.push(doc.date);
        }
        if (doc.topics && doc.topics.length) {
          metaParts.push(
            doc.topics
              .map(function (topic) {
                return "#" + topic;
              })
              .join(" ")
          );
        }

        item.innerHTML =
          '<a class="search-result-title" href="' +
          escapeHtml(doc.url) +
          '">' +
          escapeHtml(doc.title) +
          "</a>" +
          '<p class="search-result-meta">' +
          escapeHtml(metaParts.join(" · ")) +
          "</p>" +
          (doc.excerpt
            ? '<p class="search-result-excerpt">' +
              escapeHtml(doc.excerpt) +
              "</p>"
            : "");

        results.appendChild(item);
      });
    }

    function runSearch() {
      const query = input.value.trim();
      if (!query || !index) {
        renderResults([]);
        return;
      }

      try {
        const matches = searchDocuments(query, documents, index);
        renderResults(matches);
      } catch (error) {
        status.textContent = "No results.";
        results.innerHTML = "";
      }
    }

    fetch("/static/search-index.json")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Failed to load search index");
        }
        return response.json();
      })
      .then(function (data) {
        documents = data;
        index = buildIndex(documents);
        if (options.initialQuery) {
          input.value = options.initialQuery;
        }
        runSearch();
      })
      .catch(function () {
        status.textContent = "Search index could not be loaded. Run make ingest.";
      });

    input.addEventListener("input", runSearch);
  }

  window.initSearch = initSearch;

  if (document.getElementById("memex-search-input")) {
    const params = new URLSearchParams(window.location.search);
    initSearch({
      inputId: "memex-search-input",
      statusId: "memex-search-status",
      resultsId: "memex-search-results",
      initialQuery: params.get("q") || "",
      limit: 20,
    });
  }
})();
