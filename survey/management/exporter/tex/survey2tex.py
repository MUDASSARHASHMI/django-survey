# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import logging
import os
from builtins import super

import yaml
from django.conf import settings
from django.utils.text import slugify
from future import standard_library

from survey.management.exporter.survey2x import Survey2X
from survey.management.exporter.tex.latex_file import LatexFile
from survey.management.exporter.tex.question2tex import Question2Tex

standard_library.install_aliases()


LOGGER = logging.getLogger(__name__)


class Survey2Tex(Survey2X):

    ANALYSIS_FUNCTION = []

    def __init__(self, survey, configuration_file=None):
        Survey2X.__init__(self, survey)
        if configuration_file is None:
            configuration_file = settings.TEX_CONFIGURATION_FILE
        with open(configuration_file, 'r') as f:
            full_configuration = yaml.load(f)
        self.conf = full_configuration["generic"]
        specific = None
        for key in full_configuration.keys():
            if slugify(survey.name) == slugify(key):
                specific = key
        if specific is not None and full_configuration[specific] is not None:
            for key in full_configuration[specific].keys():
                try:
                    LOGGER.debug("%s (%s) : replacing '%s' by '%s'",
                                 survey.name, key, self.conf[key],
                                 full_configuration[specific][key])
                except KeyError:
                    LOGGER.debug("%s (%s): setting '%s'", survey.name, key,
                                 full_configuration[specific][key])
                self.conf[key] = full_configuration[specific][key]

    def _synthesis(self, survey):
        """ Return a String of a synthesis of the report. """
        pass

    def _additional_analysis(self, survey, latex_file):
        """ Perform additional analysis. """
        for function_ in self.ANALYSIS_FUNCTION:
            LOGGER.info("Performing additional analysis with %s", function_)
            latex_file.text += function_(survey)

    def treat_question(self, question, survey):
        LOGGER.info("Treating, %s %s", question.pk, question.text)
        chart = Question2Tex().chart(question)
        section_title = Question2Tex.html2latex(question.text)
        return u"""
\\clearpage{}
\\section{%s}

\label{sec:%s}

%s

""" % (section_title, question.pk, chart)

    def generate(self, path, output=None):
        """ Generate the pdf. """
        dir_name, file_name = os.path.split(path)
        os.chdir(dir_name)
        os.system("pwd")
        os.system("pdflatex {}".format(file_name))
        os.system("pdflatex {}".format(file_name))
        if output is not None:
            os.system("mv {}.pdf {}".format(file_name[:-3], output))
        os.chdir(settings.ROOT)

    def survey_to_x(self):
        ltxf = LatexFile(**self.conf)
        self._synthesis(self.survey)
        for question in self.survey.questions.all():
            ltxf.text += self.treat_question(question, self.survey)
        self._additional_analysis(self.survey, ltxf)
        return ltxf.document

    def generate_file(self):
        super(Survey2Tex, self).generate_file()
        self.generate(self.file_name())
