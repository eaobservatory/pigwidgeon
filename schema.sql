/* Information about a paper. */
CREATE TABLE papers(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       bibcode VARCHAR(20) NOT NULL,
       title TEXT DEFAULT "",
       abstract TEXT DEFAULT "",
       pub_openaccess INTEGER,
       refereed INTEGER,
       doi VARCHAR(20) DEFAULT "",
       first_added DATETIME NOT NULL,
       updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE identifiers (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       paper_id INTEGER NOT NULL,
       identifier VARCHAR(20) NOT NULL,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );

CREATE TABLE keywords (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       paper_id INTEGER NOT NULL,
       keyword VARCHAR(20) NOT NULL,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );

CREATE TABLE authors (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       paper_id INTEGER NOT NULL,
       author VARCHAR(20) NOT NULL,
       position_ INTEGER NOT NULL,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );

CREATE TABLE properties (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       paper_id INTEGER NOT NULL,
       property VARCHAR(30) NOT NULL,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );
/* Tables holding search info
Query has a number of paper types (simplest would be 'MATCH' and NO MATCH.).
Additionally, extra info sections can be setup.
*/

CREATE TABLE searches (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       named VARCHAR(50) NOT NULL,
       ads_query TEXT,
       last_performed TIMESTAMP,
       startdate DATETIME
);

CREATE TABLE paper_types(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
	search_id INTEGER NOT NULL,
	position_ INTEGER,
	name_ TEXT,
	name_code VARCHAR(50),
	radio BOOLEAN,
	FOREIGN KEY (search_id) REFERENCES searches(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );

CREATE TABLE info_sections(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       search_id INTEGER NOT NULL,
       position_ INTEGER,
       name_ VARCHAR(50),
       name_code VARCHAR(50),
       type_ INTEGER, /*0=radio, 1=check, 2=textarea, 3=textarea_newlines*/
       instructiontext VARCHAR(50) DEFAULT NULL,
       FOREIGN KEY (search_id) REFERENCES searches(id)
       	       ON DELETE RESTRICT ON UPDATE RESTRICT
       );

CREATE TABLE info_sublists(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       info_section_id INTEGER NOT NULL,
       named VARCHAR(50) DEFAULT NULL,
       position_ INTEGER DEFAULT NULL,
       entry_value VARCHAR(20) DEFAULT NULL,
       FOREIGN KEY (info_section_id) REFERENCES info_sections(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT
	       );

CREATE TABLE papertype_value(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       search_id INTEGER NOT NULL,
       paper_id INTEGER NOT NULL,
       username VARCHAR(50) NOT NULL,
       value_ INTEGER NOT NULL,
       datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (search_id) REFERENCES searches(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT
	  );

CREATE TABLE info_section_values(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       info_section_id INTEGER NOT NULL,
       paper_id INTEGER NOT NULL,
       username VARCHAR(50) NOT NULL,
       entered_text TEXT,
       entered_choice INTEGER,
       datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (info_section_id) REFERENCES info_sections(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT
	  );

/*Table indicating which papers match which searches.*/
CREATE TABLE paper_search_association(
       paper_id INTEGER NOT NULL,
       search_id INTEGER NOT NULL,
       FOREIGN KEY (search_id) REFERENCES searches(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT,
       FOREIGN KEY (paper_id) REFERENCES papers(id)
       	  ON DELETE RESTRICT ON UPDATE RESTRICT
	  );




INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2010SPIE.7741E..1XD",
"Extinction correction and on-sky calibration of SCUBA-2",
"Commissioning of SCUBA-2 included a program of skydips and observations of calibration sources intended to be folded into regular observing as standard methods of source flux calibration and to monitor the atmospheric opacity and stability. During commissioning, it was found that these methods could also be utilised to characterise the fundamental instrument response to sky noise and astronomical signals. Novel techniques for analysing onsky performance and atmospheric conditions are presented, along with results from the calibration observations and skydips.",
0,
0,
'10.1117/12.856476',
'2016-06-12 23:04:00');
INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2013MNRAS.430.2534D","SCUBA-2: on-sky calibration using submillimetre standard sources","SCUBA-2 is a 10 000-bolometer submillimetre camera on the James Clerk Maxwell Telescope. The instrument commissioning was completed in 2011 September, and full science operations began in 2011 October. To harness the full potential of this powerful new astronomical tool, the instrument calibration must be accurate and well understood. To this end, the algorithms for calculating the line-of-sight opacity have been improved, and the derived atmospheric extinction relationships at both wavebands of the SCUBA-2 instrument are presented. The results from over 500 primary and secondary calibrator observations have allowed accurate determination of the flux conversion factors (FCF) for the 850 and 450 μm arrays. Descriptions of the instrument beam shape and photometry methods are presented. The calibration factors are well determined, with relative calibration accuracy better than 5 per cent at 850 μm and 10 per cent at 450 μm, reflecting the success of the derived opacity relations as well as the stability of the performance of the instrument over several months. The sample size of the calibration observations and accurate FCFs have allowed the determination of the 850 and 450 μm fluxes of several well-known submillimetre sources, and these results are compared with previous measurements from SCUBA.",1,1,'10.1093/mnras/stt090','2016-06-12 23:04:00');
INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2008SPIE.7012E..3ZD","Optimizing atmospheric correction at the JCMT using a 183GHz water vapor radiometer","A 183GHz water vapour radiometer is installed at the JCMT, but is not currently used for active atmospheric calibration. With the installation of the SCUBA-2 submillimetre camera, it is desirable to provide more accurate and time-sensitive calibration at specific wavelengths. It is shown here that the 183GHz water vapour monitor data can be used to calculate the atmospheric opacity over small time-scales, directly along the line-of-sight of the instrument. These data will be used to identify the potential for improvement in existing calibration schemes, and the requirements of such a system if used with an instrument such as SCUBA-2.",0,0,"10.1117/12.787471",'2016-06-12 23:04:00');
INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2013ApJS..209....8D","CO (3 - 2) High-resolution Survey of the Galactic Plane: R1","We present the first release (R1) of data from the CO High-Resolution Survey (COHRS), which maps a strip of the inner Galactic plane in <SUP>12</SUP>CO (J = 3 → 2). The data are taken using the Heterodyne Array Receiver Programme on the James Clerk Maxwell Telescope (JCMT) in Hawaii, which has a 14 arcsec angular resolution at this frequency. When complete, this survey will cover |b| 〈= 0.°5 between 10° 〈 l 〈 65°. This first release covers |b| 〈= 0.°5 between 10.°25 〈 l 〈 17.°5 and 50.°25 〈 l 〈 55.°25, and |b| 〈= 0.°25 between 17.°5 〈 l 〈 50.°25. The data are smoothed to a velocity resolution of 1 km s<SUP>-1</SUP>, a spatial resolution of 16 arcsec and achieve a mean rms of ~1 K. COHRS data are available to the community online at <A href='http://dx.doi.org/10.11570/13.0002'>http://dx.doi.org/10.11570/13.0002</A>. In this paper we describe the data acquisition and reduction techniques used and present integrated intensity images and longitude-velocity maps. We also discuss the noise characteristics of the data. The high resolution is a powerful tool for morphological studies of bubbles and filaments while the velocity information shows the spiral arms and outflows. These data are intended to complement both existing and upcoming surveys, e.g., the Bolocam Galactic Plane Survey (BGPS), ATLASGAL, the Herschel Galactic Plane Survey (Hi-GAL) and the JCMT Galactic Plane Survey with SCUBA-2 (JPS).",1,1,"['10.1088/0067-0049/209/1/8']",'2016-06-12 23:04:00');
INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2012SPIE.8452E..02D","A new era of wide-field submillimetre imaging: on-sky performance of SCUBA-2","SCUBA-2 is the largest submillimetre wide-field bolometric camera ever built. This 43 square arc- minute field-of-view instrument operates at two wavelengths (850 and 450 microns) and has been installed on the James Clerk Maxwell Telescope on Mauna Kea, Hawaii. SCUBA-2 has been successfully commissioned and operational for general science since October 2011. This paper presents an overview of the on-sky performance of the instrument during and since commissioning in mid- 2011. The on-sky noise characteristics and NEPs of the 450 μm and 850 μm arrays, with average yields of approximately 3400 bolometers at each wavelength, will be shown. The observing modes of the instrument and the on-sky calibration techniques are described. The culmination of these efforts has resulted in a scientifically powerful mapping camera with sensitivities that allow a square degree of sky to be mapped to 10 mJy/beam rms at 850 μm in 2 hours and 60 mJy/beam rms at 450 μm in 5 hours in the best weather.",0,0,"['10.1117/12.926547']",'2016-06-12 23:04:00');
INSERT INTO papers (bibcode, title, abstract, pub_openaccess, refereed, doi, first_added) VALUES ("2014SPIE.9149E..1FD","Setting the standard: 25 years of operating the JCMT","The James Clerk Maxwell Telescope (JCMT) is the largest single-dish submillimetre telescope in the world, and throughout its lifetime the volume and impact of its science output have steadily increased. A key factor for this continuing productivity is an ever-evolving approach to optimising operations, data acquisition, and science product pipelines and archives. The JCMT was one of the first common-user telescopes to adopt flexible scheduling in 2003, and its impact over a decade of observing will be presented. The introduction of an advanced data-reduction pipeline played an integral role, both for fast real-time reduction during observing, and for science-grade reduction in support of individual projects, legacy surveys, and the JCMT Science Archive. More recently, these foundations have facilitated the commencement of remote observing in addition to traditional on-site operations to further increase on-sky science time. The contribution of highly-trained and engaged operators, support and technical staff to efficient operations will be described. The long-term returns of this evolution are presented here, noting they were achieved in face of external pressures for leaner operating budgets and reduced staffing levels. In an era when visiting observers are being phased out of many observatories, we argue that maintaining a critical level of observer participation is vital to improving and maintaining scientific productivity and facility longevity.",0,0,"['10.1117/12.2056862']",'2016-06-12 23:04:00');

INSERT INTO authors (paper_id, author, position_) VALUES(1,"Dempsey, Jessica T.",0);
INSERT INTO authors (paper_id, author, position_) VALUES(1,"Friberg, Per",1);
INSERT INTO authors (paper_id, author, position_) VALUES(1,"Jenness, Tim",2);
INSERT INTO authors (paper_id, author, position_) VALUES(1,"Bintley, Dan",3);
INSERT INTO authors (paper_id, author, position_) VALUES(1,"Holland, Wayne S.",4);
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Dempsey, J. T.",0);
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Friberg, P.","1");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Jenness, T.","2");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Tilanus, R. P. J.","3");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Thomas, H. S.","4");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Holland, W. S.","5");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Bintley, D.","6");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Berry, D. S.","7");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Chapin, E. L.","8");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Chrysostomou, A.","9");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Davis, G. R.","10");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Gibb, A. G.","11");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Parsons, H.","12");
INSERT INTO authors (paper_id, author, position_) VALUES(2,"Robson, E. I.","13");
INSERT INTO authors (paper_id, author, position_) VALUES(4,"Dempsey, Jessica T.","0");
INSERT INTO authors (paper_id, author, position_) VALUES(4,"Friberg, Per","1");
INSERT INTO authors (paper_id, author, position_) VALUES(5,"Dempsey, J. T.","0");
INSERT INTO authors (paper_id, author, position_) VALUES(5,"Thomas, H. S.","1");
INSERT INTO authors (paper_id, author, position_) VALUES(5,"Currie, M. J.","2");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Dempsey, Jessica T.","0");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Holland, Wayne S.","1");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Chrysostomou, Antonio","2");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Berry, David S.","3");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Bintley, Daniel","4");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Chapin, Edward L.","5");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Craig, Simon C.","6");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Coulson, Iain M.","7");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Davis, Gary R.","8");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Friberg, Per","9");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Jenness, Tim","10");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Gibb, Andy G.","11");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Parsons, Harriet A. L.","12");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Scott, Douglas","13");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Thomas, Holly S.","14");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Tilanus, Remo P. J.","15");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Robson, Ian","16");
INSERT INTO authors (paper_id, author, position_) VALUES(3,"Walther, Craig A.","17");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Dempsey, Jessica T.","0");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Bell, Graham S.","1");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Chrysostomou, Antonio","2");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Coulson, Iain M.","3");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Davis, Gary R.","4");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Economou, Frossie","5");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Friberg, Per","6");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Jenness, Timothy","7");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Johnstone, Doug","8");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Tilanus, Remo P. J.","9");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Thomas, Holly S.","10");
INSERT INTO authors (paper_id, author, position_) VALUES(6,"Walther, Craig A.","11");


INSERT INTO searches (named, ads_query) VALUES ('JCMT Papers', 'test ads query');

INSERT INTO paper_types(search_id, position_, name_, name_code, radio) VALUES(1, 0, 'JCMT Science Papers', 'sci', 0);
INSERT INTO paper_types(search_id, position_, name_, name_code, radio) VALUES(1, 1, 'JCMT Instrumentation Papers', 'inst', 0);
INSERT INTO paper_types(search_id, position_, name_, name_code, radio) VALUES(1, 2, 'JCMT Software papers', 'soft', 0);
INSERT INTO paper_types(search_id, position_, name_, name_code, radio) VALUES(1, 3, 'JCMT Other Papers', 'other', 0);
INSERT INTO paper_types(search_id, position_, name_, name_code, radio) VALUES(1, 4, 'Not a JCMT Paper', 'not', 0);


INSERT INTO info_sections(search_id, position_, name_, name_code, type_, instructiontext) VALUES(1, 1,'Instruments', 'inst', 1, NULL);
INSERT INTO info_sections(search_id, position_, name_, name_code, type_, instructiontext) VALUES(1, 2,'Observations', 'obs', 1, NULL);
INSERT INTO info_sections(search_id, position_, name_, name_code, type_, instructiontext) VALUES(1, 3,'Project Codes', 'codes', 3, 'Enter each code on a new line.');
INSERT INTO info_sections(search_id, position_, name_, name_code, type_, instructiontext) VALUES(1, 4,'Science Areas', 'areas', 1, NULL);
INSERT INTO info_sections(search_id, position_, name_, name_code, type_, instructiontext) VALUES(1, 5,'Notes', 'notes', 2, "");


INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(1, 'SCUBA-2', 1, 'scuba2');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(1, 'POL-2', 2, 'pol2');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(1, 'HARP', 3, 'harp');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(1, 'RxA3', 4, 'rxa3');

INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(2, 'PI', 1, 'pi');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(2, 'Archive', 2, 'archive');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(2, 'Unknown', 3, 'unkown');

INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(4, 'Star Formation/ISM', 1, 'sf');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(4, 'Cosmology', 2, 'cosmos');
INSERT INTO info_sublists(info_section_id, named, position_, entry_value) VALUES
(4, 'Solar System', 3, 'solar');



INSERT INTO paper_search_association(paper_id, search_id) VALUES(1,1);
INSERT INTO paper_search_association(paper_id, search_id) VALUES(2,1);
INSERT INTO paper_search_association(paper_id, search_id) VALUES(3,1);
INSERT INTO paper_search_association(paper_id, search_id) VALUES(4,1);
INSERT INTO paper_search_association(paper_id, search_id) VALUES(5,1);
INSERT INTO paper_search_association(paper_id, search_id) VALUES(6,1);

INSERT INTO keywords(paper_id, keyword) VALUES(1, 'Astrophysics - Instrumentation and Methods for Astrophysics');

INSERT INTO keywords(paper_id, keyword) VALUES (2, 'atmospheric effects');
INSERT INTO keywords(paper_id, keyword) VALUES (2, 'submillimetre: general');
INSERT INTO keywords(paper_id, keyword) VALUES (2, 'Astrophysics - Instrumentation and Methods for Astrophysics');

INSERT INTO properties(paper_id, property) VALUES(1, 'OPENACCESS');
INSERT INTO properties(paper_id, property) VALUES(1, 'ARTICLE');
INSERT INTO properties(paper_id, property) VALUES(1, 'NOT REFEREED');
INSERT INTO properties(paper_id, property) VALUES(1, 'EPRINT_OPENACCESS');

INSERT INTO properties(paper_id, property) VALUES(2, 'OPENACCESS');
INSERT INTO properties(paper_id, property) VALUES(2, 'ARTICLE');
INSERT INTO properties(paper_id, property) VALUES(2, 'REFEREED');
INSERT INTO properties(paper_id, property) VALUES(2, 'EPRINT_OPENACCESS');
INSERT INTO properties(paper_id, property) VALUES(2, 'PUB_OPENACCESS');


INSERT INTO identifiers(paper_id, identifier) VALUES(2, '2013arXiv1301.3773D');
INSERT INTO identifiers(paper_id, identifier) VALUES(2, '2013MNRAS.430.2534D');
INSERT INTO identifiers(paper_id, identifier) VALUES(2, '2013arXiv1301.3773D');
INSERT INTO identifiers(paper_id, identifier) VALUES(2, '10.1093/mnras/stt090');
INSERT INTO identifiers(paper_id, identifier) VALUES(2, 'arXiv:1301.3773');
