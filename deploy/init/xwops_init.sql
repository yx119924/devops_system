-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: django-vue3-admin
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `django-vue3-admin`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `django-vue3-admin` /*!40100 DEFAULT CHARACTER SET utf8 */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `django-vue3-admin`;

--
-- Table structure for table `alert_channel`
--

DROP TABLE IF EXISTS `alert_channel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_channel` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `type` varchar(16) NOT NULL,
  `config` json NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_channel_creator_id_7bc7a184` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_channel`
--

LOCK TABLES `alert_channel` WRITE;
/*!40000 ALTER TABLE `alert_channel` DISABLE KEYS */;
INSERT INTO `alert_channel` VALUES (7,'1','1','2026-08-31 09:49:08.728437','2026-08-31 09:49:08.728448','飞书告警','feishu','{\"webhook\": \"https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN\"}',1,NULL,1);
/*!40000 ALTER TABLE `alert_channel` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alert_event`
--

DROP TABLE IF EXISTS `alert_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_event` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `fingerprint` varchar(64) NOT NULL,
  `alertname` varchar(128) NOT NULL,
  `status` varchar(16) NOT NULL,
  `severity` varchar(16) NOT NULL,
  `instance` varchar(128) DEFAULT NULL,
  `summary` varchar(512) DEFAULT NULL,
  `description` varchar(1024) DEFAULT NULL,
  `labels` json NOT NULL,
  `starts_at` datetime(6) DEFAULT NULL,
  `ends_at` datetime(6) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_event_fingerprint_99989474` (`fingerprint`),
  KEY `alert_event_alertname_e8954e5f` (`alertname`),
  KEY `alert_event_creator_id_0f0f4f3f` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_event`
--

LOCK TABLES `alert_event` WRITE;
/*!40000 ALTER TABLE `alert_event` DISABLE KEYS */;
/*!40000 ALTER TABLE `alert_event` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alert_group`
--

DROP TABLE IF EXISTS `alert_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_group` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_group_creator_id_09d61b03` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_group`
--

LOCK TABLES `alert_group` WRITE;
/*!40000 ALTER TABLE `alert_group` DISABLE KEYS */;
INSERT INTO `alert_group` VALUES (5,'1','1','2026-08-31 11:02:46.128748','2026-08-31 11:02:46.128761','飞书告警',NULL,1,1);
/*!40000 ALTER TABLE `alert_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alert_group_channels`
--

DROP TABLE IF EXISTS `alert_group_channels`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_group_channels` (
  `id` int NOT NULL AUTO_INCREMENT,
  `alertgroup_id` bigint NOT NULL,
  `notifychannel_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `alert_group_channels_alertgroup_id_notifychan_0844b133_uniq` (`alertgroup_id`,`notifychannel_id`),
  KEY `alert_group_channels_alertgroup_id_17275544` (`alertgroup_id`),
  KEY `alert_group_channels_notifychannel_id_5539fac3` (`notifychannel_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_group_channels`
--

LOCK TABLES `alert_group_channels` WRITE;
/*!40000 ALTER TABLE `alert_group_channels` DISABLE KEYS */;
INSERT INTO `alert_group_channels` VALUES (4,5,7);
/*!40000 ALTER TABLE `alert_group_channels` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alert_rule`
--

DROP TABLE IF EXISTS `alert_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_rule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(128) NOT NULL,
  `expr` longtext NOT NULL,
  `duration` varchar(16) NOT NULL,
  `severity` varchar(16) NOT NULL,
  `summary` varchar(255) DEFAULT NULL,
  `description` varchar(512) DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `group_id` bigint DEFAULT NULL,
  `template_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_rule_creator_id_b2ebca64` (`creator_id`),
  KEY `alert_rule_group_id_282d778f` (`group_id`),
  KEY `alert_rule_template_id_12a29552` (`template_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_rule`
--

LOCK TABLES `alert_rule` WRITE;
/*!40000 ALTER TABLE `alert_rule` DISABLE KEYS */;
INSERT INTO `alert_rule` VALUES (2,'1','1','2026-08-31 18:22:45.340721','2026-08-28 17:39:40.957739','节点宕机告警','up == 0','1m','critical','服务器宕机','服务器宕机',1,1,5,39);
/*!40000 ALTER TABLE `alert_rule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alert_template`
--

DROP TABLE IF EXISTS `alert_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_template` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `body` longtext NOT NULL,
  `variables` json NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `alert_template_creator_id_a6560e5e` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alert_template`
--

LOCK TABLES `alert_template` WRITE;
/*!40000 ALTER TABLE `alert_template` DISABLE KEYS */;
INSERT INTO `alert_template` VALUES (35,NULL,NULL,'2026-08-31 17:40:14.720089','2026-08-31 17:40:14.720112','通用默认模板','兜底模板：未指定模板的规则触发时使用','【{{ severity | upper }}】{{ alertname }} ({{ status }})\n{% if summary %}摘要：{{ summary }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if instance %}实例：{{ instance }}\n{% endif %}{% if value %}当前值：{{ value }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"status\", \"summary\", \"value\"]',1,1,NULL),(36,NULL,NULL,'2026-08-31 17:40:14.725344','2026-08-31 17:40:14.725357','CPU 使用率过高','适用于 CPU 使用率类告警（node_cpu / process_cpu）','【{{ severity | upper }}】CPU 使用率告警：{{ alertname }}\n实例：{{ instance }}\n{% if value %}当前值：{{ value }}\n{% endif %}{% if summary %}摘要：{{ summary }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"summary\", \"value\"]',0,1,NULL),(37,NULL,NULL,'2026-08-31 17:40:14.729716','2026-08-31 17:40:14.729727','内存使用率过高','适用于内存使用率类告警（node_memory）','【{{ severity | upper }}】内存使用率告警：{{ alertname }}\n实例：{{ instance }}\n{% if value %}当前值：{{ value }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"value\"]',0,1,NULL),(38,NULL,NULL,'2026-08-31 17:40:14.733288','2026-08-31 17:40:14.733297','磁盘空间不足','适用于磁盘空间/文件系统用量类告警（node_filesystem）','【{{ severity | upper }}】磁盘空间告警：{{ alertname }}\n实例：{{ instance }}\n{% if value %}当前值：{{ value }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"value\"]',0,1,NULL),(39,NULL,NULL,'2026-08-31 17:40:14.737240','2026-08-31 17:40:14.737250','节点宕机（主机不可达）','适用于主机不可达类告警（up == 0 / ping 失败）','【{{ severity | upper }}】主机宕机告警：{{ alertname }}\n实例：{{ instance }}\n状态：{{ status }}\n{% if summary %}摘要：{{ summary }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"status\", \"summary\"]',0,1,NULL),(40,NULL,NULL,'2026-08-31 17:40:14.741496','2026-08-31 17:40:14.741506','服务/端口不可用','适用于服务健康/端口探测类告警（probe / blackbox_exporter）','【{{ severity | upper }}】服务健康告警：{{ alertname }}\n实例：{{ instance }}\n{% if summary %}摘要：{{ summary }}\n{% endif %}{% if description %}描述：{{ description }}\n{% endif %}{% if value %}当前值：{{ value }}\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\n{% endif %}','[\"alertname\", \"description\", \"instance\", \"severity\", \"startsAt\", \"summary\", \"value\"]',0,1,NULL);
/*!40000 ALTER TABLE `alert_template` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=205 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add permission',1,'add_permission'),(2,'Can change permission',1,'change_permission'),(3,'Can delete permission',1,'delete_permission'),(4,'Can view permission',1,'view_permission'),(5,'Can add group',2,'add_group'),(6,'Can change group',2,'change_group'),(7,'Can delete group',2,'delete_group'),(8,'Can view group',2,'view_group'),(9,'Can add content type',3,'add_contenttype'),(10,'Can change content type',3,'change_contenttype'),(11,'Can delete content type',3,'delete_contenttype'),(12,'Can view content type',3,'view_contenttype'),(13,'Can add session',4,'add_session'),(14,'Can change session',4,'change_session'),(15,'Can delete session',4,'delete_session'),(16,'Can view session',4,'view_session'),(17,'Can add captcha store',5,'add_captchastore'),(18,'Can change captcha store',5,'change_captchastore'),(19,'Can delete captcha store',5,'delete_captchastore'),(20,'Can view captcha store',5,'view_captchastore'),(21,'Can add 用户表',6,'add_users'),(22,'Can change 用户表',6,'change_users'),(23,'Can delete 用户表',6,'delete_users'),(24,'Can view 用户表',6,'view_users'),(25,'Can add 部门表',7,'add_dept'),(26,'Can change 部门表',7,'change_dept'),(27,'Can delete 部门表',7,'delete_dept'),(28,'Can view 部门表',7,'view_dept'),(29,'Can add 菜单表',8,'add_menu'),(30,'Can change 菜单表',8,'change_menu'),(31,'Can delete 菜单表',8,'delete_menu'),(32,'Can view 菜单表',8,'view_menu'),(33,'Can add 菜单权限表',9,'add_menubutton'),(34,'Can change 菜单权限表',9,'change_menubutton'),(35,'Can delete 菜单权限表',9,'delete_menubutton'),(36,'Can view 菜单权限表',9,'view_menubutton'),(37,'Can add 消息中心',10,'add_messagecenter'),(38,'Can change 消息中心',10,'change_messagecenter'),(39,'Can delete 消息中心',10,'delete_messagecenter'),(40,'Can view 消息中心',10,'view_messagecenter'),(41,'Can add 角色表',11,'add_role'),(42,'Can change 角色表',11,'change_role'),(43,'Can delete 角色表',11,'delete_role'),(44,'Can view 角色表',11,'view_role'),(45,'Can add 角色菜单权限表',12,'add_rolemenupermission'),(46,'Can change 角色菜单权限表',12,'change_rolemenupermission'),(47,'Can delete 角色菜单权限表',12,'delete_rolemenupermission'),(48,'Can view 角色菜单权限表',12,'view_rolemenupermission'),(49,'Can add 角色按钮权限表',13,'add_rolemenubuttonpermission'),(50,'Can change 角色按钮权限表',13,'change_rolemenubuttonpermission'),(51,'Can delete 角色按钮权限表',13,'delete_rolemenubuttonpermission'),(52,'Can view 角色按钮权限表',13,'view_rolemenubuttonpermission'),(53,'Can add 岗位表',14,'add_post'),(54,'Can change 岗位表',14,'change_post'),(55,'Can delete 岗位表',14,'delete_post'),(56,'Can view 岗位表',14,'view_post'),(57,'Can add 操作日志',15,'add_operationlog'),(58,'Can change 操作日志',15,'change_operationlog'),(59,'Can delete 操作日志',15,'delete_operationlog'),(60,'Can view 操作日志',15,'view_operationlog'),(61,'Can add 消息中心目标用户表',16,'add_messagecentertargetuser'),(62,'Can change 消息中心目标用户表',16,'change_messagecentertargetuser'),(63,'Can delete 消息中心目标用户表',16,'delete_messagecentertargetuser'),(64,'Can view 消息中心目标用户表',16,'view_messagecentertargetuser'),(65,'Can add 菜单字段表',17,'add_menufield'),(66,'Can change 菜单字段表',17,'change_menufield'),(67,'Can delete 菜单字段表',17,'delete_menufield'),(68,'Can view 菜单字段表',17,'view_menufield'),(69,'Can add 登录日志',18,'add_loginlog'),(70,'Can change 登录日志',18,'change_loginlog'),(71,'Can delete 登录日志',18,'delete_loginlog'),(72,'Can view 登录日志',18,'view_loginlog'),(73,'Can add 文件管理',19,'add_filelist'),(74,'Can change 文件管理',19,'change_filelist'),(75,'Can delete 文件管理',19,'delete_filelist'),(76,'Can view 文件管理',19,'view_filelist'),(77,'Can add 字段权限表',20,'add_fieldpermission'),(78,'Can change 字段权限表',20,'change_fieldpermission'),(79,'Can delete 字段权限表',20,'delete_fieldpermission'),(80,'Can view 字段权限表',20,'view_fieldpermission'),(81,'Can add 下载中心',21,'add_downloadcenter'),(82,'Can change 下载中心',21,'change_downloadcenter'),(83,'Can delete 下载中心',21,'delete_downloadcenter'),(84,'Can view 下载中心',21,'view_downloadcenter'),(85,'Can add 字典表',22,'add_dictionary'),(86,'Can change 字典表',22,'change_dictionary'),(87,'Can delete 字典表',22,'delete_dictionary'),(88,'Can view 字典表',22,'view_dictionary'),(89,'Can add 地区表',23,'add_area'),(90,'Can change 地区表',23,'change_area'),(91,'Can delete 地区表',23,'delete_area'),(92,'Can view 地区表',23,'view_area'),(93,'Can add 接口白名单',24,'add_apiwhitelist'),(94,'Can change 接口白名单',24,'change_apiwhitelist'),(95,'Can delete 接口白名单',24,'delete_apiwhitelist'),(96,'Can view 接口白名单',24,'view_apiwhitelist'),(97,'Can add 系统配置表',25,'add_systemconfig'),(98,'Can change 系统配置表',25,'change_systemconfig'),(99,'Can delete 系统配置表',25,'delete_systemconfig'),(100,'Can view 系统配置表',25,'view_systemconfig'),(101,'Can add 博客',26,'add_blog'),(102,'Can change 博客',26,'change_blog'),(103,'Can delete 博客',26,'delete_blog'),(104,'Can view 博客',26,'view_blog'),(105,'Can add 产品',27,'add_product'),(106,'Can change 产品',27,'change_product'),(107,'Can delete 产品',27,'delete_product'),(108,'Can view 产品',27,'view_product'),(109,'Can add crontab',28,'add_crontabschedule'),(110,'Can change crontab',28,'change_crontabschedule'),(111,'Can delete crontab',28,'delete_crontabschedule'),(112,'Can view crontab',28,'view_crontabschedule'),(113,'Can add interval',29,'add_intervalschedule'),(114,'Can change interval',29,'change_intervalschedule'),(115,'Can delete interval',29,'delete_intervalschedule'),(116,'Can view interval',29,'view_intervalschedule'),(117,'Can add periodic task',30,'add_periodictask'),(118,'Can change periodic task',30,'change_periodictask'),(119,'Can delete periodic task',30,'delete_periodictask'),(120,'Can view periodic task',30,'view_periodictask'),(121,'Can add periodic task track',31,'add_periodictasks'),(122,'Can change periodic task track',31,'change_periodictasks'),(123,'Can delete periodic task track',31,'delete_periodictasks'),(124,'Can view periodic task track',31,'view_periodictasks'),(125,'Can add solar event',32,'add_solarschedule'),(126,'Can change solar event',32,'change_solarschedule'),(127,'Can delete solar event',32,'delete_solarschedule'),(128,'Can view solar event',32,'view_solarschedule'),(129,'Can add clocked',33,'add_clockedschedule'),(130,'Can change clocked',33,'change_clockedschedule'),(131,'Can delete clocked',33,'delete_clockedschedule'),(132,'Can view clocked',33,'view_clockedschedule'),(133,'Can add chord counter',34,'add_chordcounter'),(134,'Can change chord counter',34,'change_chordcounter'),(135,'Can delete chord counter',34,'delete_chordcounter'),(136,'Can view chord counter',34,'view_chordcounter'),(137,'Can add task result',35,'add_taskresult'),(138,'Can change task result',35,'change_taskresult'),(139,'Can delete task result',35,'delete_taskresult'),(140,'Can view task result',35,'view_taskresult'),(141,'Can add group result',36,'add_groupresult'),(142,'Can change group result',36,'change_groupresult'),(143,'Can delete group result',36,'delete_groupresult'),(144,'Can view group result',36,'view_groupresult'),(145,'Can add 业务线',37,'add_businessline'),(146,'Can change 业务线',37,'change_businessline'),(147,'Can delete 业务线',37,'delete_businessline'),(148,'Can view 业务线',37,'view_businessline'),(149,'Can add 机房',38,'add_idc'),(150,'Can change 机房',38,'change_idc'),(151,'Can delete 机房',38,'delete_idc'),(152,'Can view 机房',38,'view_idc'),(153,'Can add 服务器',39,'add_server'),(154,'Can change 服务器',39,'change_server'),(155,'Can delete 服务器',39,'delete_server'),(156,'Can view 服务器',39,'view_server'),(157,'Can add 环境',40,'add_environment'),(158,'Can change 环境',40,'change_environment'),(159,'Can delete 环境',40,'delete_environment'),(160,'Can view 环境',40,'view_environment'),(161,'Can add 会话记录',41,'add_sessionrecord'),(162,'Can change 会话记录',41,'change_sessionrecord'),(163,'Can delete 会话记录',41,'delete_sessionrecord'),(164,'Can view 会话记录',41,'view_sessionrecord'),(165,'Can add 凭据',42,'add_credential'),(166,'Can change 凭据',42,'change_credential'),(167,'Can delete 凭据',42,'delete_credential'),(168,'Can view 凭据',42,'view_credential'),(169,'Can add 命令审计',43,'add_commandlog'),(170,'Can change 命令审计',43,'change_commandlog'),(171,'Can delete 命令审计',43,'delete_commandlog'),(172,'Can view 命令审计',43,'view_commandlog'),(173,'Can add Prometheus 数据源',44,'add_prometheussource'),(174,'Can change Prometheus 数据源',44,'change_prometheussource'),(175,'Can delete Prometheus 数据源',44,'delete_prometheussource'),(176,'Can view Prometheus 数据源',44,'view_prometheussource'),(177,'Can add 告警规则',45,'add_alertrule'),(178,'Can change 告警规则',45,'change_alertrule'),(179,'Can delete 告警规则',45,'delete_alertrule'),(180,'Can view 告警规则',45,'view_alertrule'),(181,'Can add 通知渠道',46,'add_notifychannel'),(182,'Can change 通知渠道',46,'change_notifychannel'),(183,'Can delete 通知渠道',46,'delete_notifychannel'),(184,'Can view 通知渠道',46,'view_notifychannel'),(185,'Can add 告警群组',47,'add_alertgroup'),(186,'Can change 告警群组',47,'change_alertgroup'),(187,'Can delete 告警群组',47,'delete_alertgroup'),(188,'Can view 告警群组',47,'view_alertgroup'),(189,'Can add 命令下发结果',48,'add_commanddispatchitem'),(190,'Can change 命令下发结果',48,'change_commanddispatchitem'),(191,'Can delete 命令下发结果',48,'delete_commanddispatchitem'),(192,'Can view 命令下发结果',48,'view_commanddispatchitem'),(193,'Can add 命令下发',49,'add_commanddispatch'),(194,'Can change 命令下发',49,'change_commanddispatch'),(195,'Can delete 命令下发',49,'delete_commanddispatch'),(196,'Can view 命令下发',49,'view_commanddispatch'),(197,'Can add 告警事件',50,'add_alertevent'),(198,'Can change 告警事件',50,'change_alertevent'),(199,'Can delete 告警事件',50,'delete_alertevent'),(200,'Can view 告警事件',50,'view_alertevent'),(201,'Can add 告警模板',51,'add_alerttemplate'),(202,'Can change 告警模板',51,'change_alerttemplate'),(203,'Can delete 告警模板',51,'delete_alerttemplate'),(204,'Can view 告警模板',51,'view_alerttemplate');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bastion_command_dispatch`
--

DROP TABLE IF EXISTS `bastion_command_dispatch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bastion_command_dispatch` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(128) NOT NULL,
  `command` longtext NOT NULL,
  `targets` json NOT NULL,
  `timeout` int NOT NULL,
  `status` varchar(20) NOT NULL,
  `total` int NOT NULL,
  `success_count` int NOT NULL,
  `failed_count` int NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `finished_at` datetime(6) DEFAULT NULL,
  `last_error` longtext,
  `creator_id` bigint DEFAULT NULL,
  `credential_id` bigint DEFAULT NULL,
  `max_workers` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `bastion_command_dispatch_creator_id_04e56483` (`creator_id`),
  KEY `bastion_command_dispatch_credential_id_cd07533c` (`credential_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bastion_command_dispatch`
--

LOCK TABLES `bastion_command_dispatch` WRITE;
/*!40000 ALTER TABLE `bastion_command_dispatch` DISABLE KEYS */;
INSERT INTO `bastion_command_dispatch` VALUES (2,NULL,'1','1','2026-08-31 11:44:08.403973','2026-08-31 11:44:08.403985','查看内存','free -h','[{\"ip\": \"YOUR_SERVER_IP\", \"label\": \"YOUR_SERVER_IP\", \"ssh_port\": 22, \"server_id\": 1}]',30,'success',1,1,0,'2026-08-31 13:34:39.481678','2026-08-31 13:34:39.695738','',1,2,10),(3,NULL,'1','1','2026-08-31 13:21:55.466566','2026-08-31 13:21:55.466576','查看磁盘使用','df -h','[{\"ip\": \"YOUR_SERVER_IP\", \"label\": \"YOUR_SERVER_IP\", \"ssh_port\": 22, \"server_id\": 1}]',30,'success',1,1,0,'2026-08-31 14:26:41.770255','2026-08-31 14:26:41.982473','',1,2,10);
/*!40000 ALTER TABLE `bastion_command_dispatch` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bastion_command_dispatch_item`
--

DROP TABLE IF EXISTS `bastion_command_dispatch_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bastion_command_dispatch_item` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `label` varchar(128) NOT NULL,
  `ip` varchar(64) NOT NULL,
  `status` varchar(20) NOT NULL,
  `stdout` longtext NOT NULL,
  `stderr` longtext NOT NULL,
  `exit_code` int DEFAULT NULL,
  `duration` double DEFAULT NULL,
  `error` varchar(512) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `dispatch_id` bigint NOT NULL,
  `server_id` bigint DEFAULT NULL,
  `ssh_port` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `bastion_command_dispatch_item_creator_id_188cee2c` (`creator_id`),
  KEY `bastion_command_dispatch_item_dispatch_id_42d74193` (`dispatch_id`),
  KEY `bastion_command_dispatch_item_server_id_0a8b7a2b` (`server_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bastion_command_dispatch_item`
--

LOCK TABLES `bastion_command_dispatch_item` WRITE;
/*!40000 ALTER TABLE `bastion_command_dispatch_item` DISABLE KEYS */;
INSERT INTO `bastion_command_dispatch_item` VALUES (2,NULL,NULL,NULL,'2026-08-31 11:44:08.406901','2026-08-31 11:44:08.406913','YOUR_SERVER_IP','YOUR_SERVER_IP','success','               total        used        free      shared  buff/cache   available\nMem:           7.1Gi       2.6Gi       2.8Gi       3.3Mi       2.1Gi       4.5Gi\nSwap:             0B          0B          0B\n','',0,0.205,'',NULL,2,1,22),(3,NULL,NULL,NULL,'2026-08-31 13:21:55.470729','2026-08-31 13:21:55.470739','YOUR_SERVER_IP','YOUR_SERVER_IP','success','Filesystem      Size  Used Avail Use% Mounted on\ntmpfs           732M  1.8M  731M   1% /run\n/dev/vda1        99G   57G   39G  60% /\ntmpfs           3.6G     0  3.6G   0% /dev/shm\ntmpfs           5.0M     0  5.0M   0% /run/lock\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/87f5ab1a32782e94f4e18d90d7a9d9fb8633e388a67067dd395a9d8ea6a8f17b\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/7bff6e6d436494389e1596870e18e0138f35e9a3b058c27bf06d9ff1005b340d\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/3d44684522859a62ca7d64a2820098309e05695d11ba3784af7834aa83f1ce0e\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/85b14ae4f2d75869cdfa885a43fe78c77f958c6500f7ddce3b8a81a184d49758\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/f607461062be3eee7d56f3d4a3466aed3a38d51e134162e7e10fc302957dff7c\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/750e3271a3465f25d1ee4df7b0b7e89ba1015d1c43959de8777f29aef379049f\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/0901af662e8865cfeb5a8439881e16dde23e27ccdbf60bc8d624326f628d24aa\ntmpfs           732M   12K  732M   1% /run/user/0\noverlay          99G   57G   39G  60% /var/lib/docker/rootfs/overlayfs/9b9affb4cd08ac157233b7e08b4128986fe3db90a71251fe0a536ef302c50908\n','',0,0.2,'',NULL,3,1,22);
/*!40000 ALTER TABLE `bastion_command_dispatch_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bastion_command_log`
--

DROP TABLE IF EXISTS `bastion_command_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bastion_command_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `command` longtext NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `is_dangerous` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `session_id` bigint DEFAULT NULL,
  `dispatch_id` bigint DEFAULT NULL,
  `ip` varchar(64) DEFAULT NULL,
  `source` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `bastion_command_log_creator_id_29bd916d` (`creator_id`),
  KEY `bastion_command_log_session_id_1cd139cb` (`session_id`),
  KEY `bastion_command_log_dispatch_id_22b0bc4a` (`dispatch_id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bastion_command_log`
--

LOCK TABLES `bastion_command_log` WRITE;
/*!40000 ALTER TABLE `bastion_command_log` DISABLE KEYS */;
INSERT INTO `bastion_command_log` VALUES (1,NULL,NULL,NULL,'2026-08-28 14:11:06.185779','2026-08-28 14:11:06.185794','id','2026-08-28 14:11:06.185807',0,NULL,6,NULL,NULL,'session'),(2,NULL,NULL,NULL,'2026-08-28 14:27:47.005037','2026-08-28 14:27:47.005060','df -h','2026-08-28 14:27:47.005075',0,NULL,7,NULL,NULL,'session'),(3,NULL,NULL,NULL,'2026-08-28 14:27:52.791211','2026-08-28 14:27:52.791233','mkdir /data','2026-08-28 14:27:52.791247',0,NULL,7,NULL,NULL,'session'),(11,NULL,NULL,NULL,'2026-08-31 14:26:41.978887','2026-08-31 14:26:41.978908','df -h','2026-08-31 14:26:41.978919',0,1,NULL,3,'YOUR_SERVER_IP','dispatch');
/*!40000 ALTER TABLE `bastion_command_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bastion_credential`
--

DROP TABLE IF EXISTS `bastion_credential`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bastion_credential` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `username` varchar(64) NOT NULL,
  `auth_type` varchar(20) NOT NULL,
  `password` longtext,
  `private_key` longtext,
  `creator_id` bigint DEFAULT NULL,
  `server_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `bastion_credential_creator_id_48518d62` (`creator_id`),
  KEY `bastion_credential_server_id_73354473` (`server_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bastion_credential`
--

LOCK TABLES `bastion_credential` WRITE;
/*!40000 ALTER TABLE `bastion_credential` DISABLE KEYS */;
/*!40000 ALTER TABLE `bastion_credential` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bastion_session`
--

DROP TABLE IF EXISTS `bastion_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bastion_session` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `username` varchar(64) DEFAULT NULL,
  `ip` varchar(64) DEFAULT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration` int DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `recording` varchar(512) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `credential_id` bigint DEFAULT NULL,
  `server_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `bastion_session_creator_id_81619b7c` (`creator_id`),
  KEY `bastion_session_credential_id_42cd2ab7` (`credential_id`),
  KEY `bastion_session_server_id_d6242f9c` (`server_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bastion_session`
--

LOCK TABLES `bastion_session` WRITE;
/*!40000 ALTER TABLE `bastion_session` DISABLE KEYS */;
INSERT INTO `bastion_session` VALUES (1,NULL,NULL,NULL,'2026-08-28 12:40:37.991057','2026-08-28 12:40:37.991084','root','YOUR_SERVER_IP','2026-08-28 12:40:37.991097','2026-08-28 12:40:46.042067',8,'closed',NULL,1,2,1),(2,NULL,NULL,NULL,'2026-08-28 13:43:36.484212','2026-08-28 13:43:36.484236','root','YOUR_SERVER_IP','2026-08-28 13:43:36.484252','2026-08-28 13:43:54.690367',18,'closed',NULL,1,2,1),(3,NULL,NULL,NULL,'2026-08-28 13:52:53.097318','2026-08-28 13:52:53.097341','root','YOUR_SERVER_IP','2026-08-28 13:52:53.097350','2026-08-28 13:53:01.150522',8,'closed',NULL,1,NULL,1),(4,NULL,NULL,NULL,'2026-08-28 14:07:52.143227','2026-08-28 14:07:52.143251','root','YOUR_SERVER_IP','2026-08-28 14:07:52.143261','2026-08-28 14:07:56.276019',4,'closed',NULL,1,2,1),(5,NULL,NULL,NULL,'2026-08-28 14:08:56.718261','2026-08-28 14:08:56.718287','root','YOUR_SERVER_IP','2026-08-28 14:08:56.718297','2026-08-28 14:08:58.008770',1,'closed',NULL,1,2,1),(6,NULL,NULL,NULL,'2026-08-28 14:11:06.175618','2026-08-28 14:11:06.175647','root','YOUR_SERVER_IP','2026-08-28 14:11:06.175660','2026-08-28 14:11:06.225674',0,'closed','media/sessions/6.cast',1,NULL,1),(7,NULL,NULL,NULL,'2026-08-28 14:27:44.734735','2026-08-28 14:27:44.734774','root','YOUR_SERVER_IP','2026-08-28 14:27:44.734792','2026-08-28 14:27:54.649884',9,'closed','media/sessions/7.cast',1,2,1);
/*!40000 ALTER TABLE `bastion_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `captcha_captchastore`
--

DROP TABLE IF EXISTS `captcha_captchastore`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `captcha_captchastore` (
  `id` int NOT NULL AUTO_INCREMENT,
  `challenge` varchar(32) NOT NULL,
  `response` varchar(32) NOT NULL,
  `hashkey` varchar(40) NOT NULL,
  `expiration` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `hashkey` (`hashkey`)
) ENGINE=InnoDB AUTO_INCREMENT=118 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `captcha_captchastore`
--

LOCK TABLES `captcha_captchastore` WRITE;
/*!40000 ALTER TABLE `captcha_captchastore` DISABLE KEYS */;
INSERT INTO `captcha_captchastore` VALUES (1,'8+4=','12','b5ab885bcec37803ecdeadf39c5a7f22304018ef','2026-08-27 18:11:52.725982'),(3,'9+2=','11','64608d6afbfd75c0bb32b16f588254b7f609e83c','2026-08-27 18:13:15.510890'),(11,'6*1=','6','941775e6f76f6e2b7d379e824dfedf0aa4bdcc91','2026-08-28 15:33:42.525458'),(12,'10-8=','2','dfb242b91f415d7ad9057e36f23bdd32d6624dc1','2026-08-28 15:33:44.822035'),(13,'3*5=','15','cf8e0f393fd374226e4616990017ff3b6c41bd27','2026-08-28 15:33:50.649119'),(14,'5-5=','0','8c15fda4e5020dc05065cc3dc379374ee4eed8a8','2026-08-28 15:34:08.472261'),(15,'1+2=','3','7417dfac25d3f22c11cae91cd16f236c44dc09de','2026-08-28 15:35:32.009951'),(16,'9*5=','45','d6ac18d2ef505ffd111e4d12c5ebca6d554c7fce','2026-08-28 15:42:11.928394'),(17,'6+1=','7','3cebff5689299e1e85ab5c54d9b102477b6888f5','2026-08-28 15:45:01.238888'),(18,'4*2=','8','a53e3043b4a94a6c0079ae55adb2bdc4fe9ebd82','2026-08-28 15:45:10.686333'),(19,'7-4=','3','288887bad483b737eb519b1723f38a72dbf926a9','2026-08-28 15:45:22.232557'),(20,'10-8=','2','11612efc179b4804388016febdb937d601939789','2026-08-28 15:47:06.365110'),(21,'5+6=','11','6206fb23048178fc10c62f9b0b758f38658cae00','2026-08-28 15:48:37.574889'),(23,'9+10=','19','59f8b6c1a64003f32f845cceb8b50da84c7b5b5f','2026-08-28 15:50:35.114128'),(24,'3+8=','11','9794615a04712d8f4600f9c0cbb5cb315af4e61c','2026-08-28 15:50:42.401107'),(25,'5+3=','8','eb4733a590cabbe7c9327f8f841ac9ee980143ec','2026-08-28 15:51:00.783186'),(26,'6+5=','11','ea97ca1cfaa0ab1b4800c1c831f142aafef48966','2026-08-28 15:52:55.002116'),(27,'7+1=','8','5d8ddbda42951fccf7d51d43fb93a66cedbb6cc8','2026-08-28 15:53:06.095303'),(28,'7-1=','6','254791f989ec2051a6d45920f15e31dabfcfdd5b','2026-08-28 15:59:11.081052'),(32,'8+2=','10','d478c6add8ebe822212dacb827fa0270da7c2170','2026-08-31 09:58:14.987820'),(33,'3-3=','0','fe52473a1d76bdc816ad3df8882f338ca855dc15','2026-08-31 10:00:21.367363'),(34,'9-2=','7','d0995cb1867a0b325f133f02457b890ccfea9c8d','2026-08-31 10:02:22.800743'),(35,'3+10=','13','3f535aff6e0f762287a2ce4b89fe69d14d10ec19','2026-08-31 10:04:06.345817'),(36,'8-5=','3','8ea476e9caaa953247e3d7b81ffc07edb729f9c1','2026-08-31 10:04:40.541230'),(37,'8-4=','4','a11da73f47f25aa61af2de8f4640f73086111324','2026-08-31 10:06:16.183871'),(38,'6-4=','2','5b748a2dbb71cd9740fc17931c68ea0e8c5b2cd7','2026-08-31 10:07:40.583689'),(39,'8+4=','12','08b0f45dfa8db0089c9b3c16bd6a75028c0b4242','2026-08-31 10:09:55.530957'),(40,'10+5=','15','b1c3f8d5f3aad4fc63fcb8bc18be3d364c55a27d','2026-08-31 10:11:25.499437'),(41,'7-6=','1','2db576fe282e2c80da5d11bf06c2c903db010998','2026-08-31 10:11:51.492054'),(42,'3*4=','12','70a074eb3cbb74cf23daf45c05765e5b2e55722a','2026-08-31 10:13:08.277668'),(43,'10*10=','100','f11cacb2bd52f4425b4cf87a435132663e6e6306','2026-08-31 10:14:33.806451'),(44,'2-2=','0','596fbbf68d0836a46060880d9251aa29c6c5b215','2026-08-31 10:14:54.065196'),(45,'1*3=','3','b152c89e42c7faf957ddbfc131d807153ab76bdc','2026-08-31 10:16:00.464804'),(46,'1+2=','3','51de7f6558d79da38bb97f8dfd85ceaf58c860b3','2026-08-31 10:17:07.938675'),(47,'1*8=','8','e1ac6fafaacc15ecd7330099fa4c8c85b93db19c','2026-08-31 10:18:49.790275'),(48,'9-5=','4','3bf38293ea2b56f39be7f466aa7598f1e22f9f00','2026-08-31 10:19:55.150615'),(49,'5-4=','1','5ae270d93dd9bd78fa0332a222de6aeb3729e860','2026-08-31 10:20:16.094342'),(50,'1*3=','3','65ef69a9df4ff9a13f883b680063d4a276bd45f8','2026-08-31 10:21:19.927288'),(51,'9+10=','19','b49c53a1247a8272ab5f6b0b77d05c64ce07b982','2026-08-31 10:21:40.642857'),(52,'8-8=','0','6eea289a6a179705f99f4f8247fc20402d596b73','2026-08-31 10:22:42.623661'),(53,'7-1=','6','d571719f02ac7de4157c3c23c08dbbc958760caa','2026-08-31 10:32:28.500984'),(54,'4*7=','28','eb4e53f3aa90329a065259950d2a7b6ffa09a388','2026-08-31 10:35:00.035060'),(55,'9*1=','9','4f4b041d162980c3fdc1a968377bb6b4900fdf78','2026-08-31 10:45:07.068183'),(56,'5-5=','0','6d02f7fa83b91fb3b41e81c0acb446ab23adbb7c','2026-08-31 10:53:47.426417'),(57,'8-4=','4','5777d03e043ecbb265331202b3d4b231576fc5a3','2026-08-31 10:55:55.707012'),(58,'7-3=','4','4d64ea74f6ed08c5cc8f040a755c2c5c459ca635','2026-08-31 10:58:48.389449'),(59,'2+10=','12','78c992d5deb622c2d8daaae699f8f4e64159eedf','2026-08-31 11:00:03.982056'),(60,'6*2=','12','43dc5ba03f45549854b832e6d17926ac21453f48','2026-08-31 11:37:19.745428'),(61,'7+1=','8','70bd3dc6b9c5d1d8106a8a9365167155c61d67e8','2026-08-31 11:38:37.098814'),(62,'9-8=','1','dc372cccde49bd64e7ad6f541c067452b166e8b2','2026-08-31 11:39:12.355569'),(63,'6+10=','16','7faf8b65d36f415dad88389158678e30b2bf04c9','2026-08-31 11:41:04.552280'),(64,'1+2=','3','5e08448a8ba6732f20299713cb6d2e876d8dc5f8','2026-08-31 11:43:32.632278'),(65,'10-6=','4','ee1f68bf3cdcdfda831e0a961a757373b16df344','2026-08-31 11:55:25.582890'),(66,'8+10=','18','ed73496474189adb162b341c3a97873671fbf539','2026-08-31 11:55:58.503255'),(67,'10+6=','16','627c827c05f1fe1abca99cd50a63f066dd435973','2026-08-31 11:57:23.302747'),(68,'4+6=','10','3266372bb5c51598bf2ed1a701218ae13e34d8ec','2026-08-31 11:58:39.834458'),(69,'7+3=','10','02f938621cdbf22d8dcb4a1611ee0d267988125a','2026-08-31 12:00:25.009160'),(70,'10-1=','9','a77642bb01bf12a714b34b88f004dde93f0772aa','2026-08-31 12:00:49.492218'),(71,'2*3=','6','8f88f52b641e7c21c64021d00a5cd9a91feeef04','2026-08-31 12:01:24.316360'),(72,'4*7=','28','e4412096b8181d43b08f0745d9745574acce81f8','2026-08-31 12:04:31.562008'),(73,'10-10=','0','d9dabed4991761ad77004b1c1ad49014941fe553','2026-08-31 12:07:10.312664'),(74,'5+9=','14','443a8f4b4ac32833c7a9fd0a68129d1ca0d7735f','2026-08-31 12:12:58.287142'),(76,'1+8=','9','2fc5420380a0845204adb3985c3f685824999272','2026-08-31 13:26:47.059134'),(77,'6-2=','4','b730387b2d10d92f70bd51d726304ea31824a221','2026-08-31 13:30:26.744359'),(78,'6*4=','24','ca29e52fbc70c28cda5c6f04da47d8be8ff40dc5','2026-08-31 13:31:03.256630'),(79,'5-4=','1','e8e4f4df1b4b602b4b475016b2c8f75c04619c99','2026-08-31 13:33:36.930018'),(80,'2+4=','6','b0be40faf0997b55d95cdb46c0e1299fb6bf9e56','2026-08-31 13:57:39.284447'),(81,'1*6=','6','f555122627b6574c1a6344b6afc50af0204008f9','2026-08-31 14:00:04.478450'),(82,'3*6=','18','b02fb3a5860bc63abc855df8759218fba12eaaa0','2026-08-31 14:21:04.146767'),(83,'4-3=','1','8a6462f0d892e5ff73e721c4c21360c2a256502c','2026-08-31 15:22:04.945966'),(85,'8-7=','1','f9d1bddaf11c900759c74154f15515e64d31ec99','2026-08-31 15:31:54.429305'),(88,'10-3=','7','f5f0d2ef51d011e596b06167fb293f018f94b725','2026-08-31 15:36:30.489512'),(89,'10-5=','5','25eaeef85ddce5094312667ae5e3961b7c2a2719','2026-08-31 15:40:47.061057'),(90,'8-1=','7','dcd73ffbed6dea2358f6a8da0472dd80929abd72','2026-08-31 16:02:15.209481'),(91,'2+3=','5','ed981ce5b9d333d047cf72313eac5ada692f8691','2026-08-31 16:03:42.286726'),(92,'10*10=','100','43e06ec83e82cca4ac91c609bd865d69bd4b35eb','2026-08-31 16:04:23.527240'),(93,'9*7=','63','1373ae6ef2958914c7948484c7c59c2d2a7bcfff','2026-08-31 16:05:17.292957'),(94,'6*1=','6','5baa061f270ec5114c65f8f4f1862620df852b05','2026-08-31 16:06:15.936500'),(95,'2-2=','0','b01eeb6bc4674a81052a13a9ff1f01f5b624fb22','2026-08-31 16:07:32.037376'),(96,'6-2=','4','d7e0e151bfa39a9e05817e467d60071dba436c52','2026-08-31 16:08:19.658882'),(97,'4+4=','8','8962b5801be80dd4f8b5a57537fd11ee31124502','2026-08-31 16:09:00.722479'),(98,'9+7=','16','9a7daef137f2577d2e3c5975bd6f86249f0222f5','2026-08-31 16:09:26.701079'),(99,'10*4=','40','8fddf84d00485ced63cbab8e4de19b04db01ea9c','2026-08-31 16:09:49.424139'),(100,'8-7=','1','678ad07d74176bd25f77bed0bddba12de41e6b04','2026-08-31 16:17:18.477621'),(101,'6*5=','30','ad12abdd01548050a7e36661aeee9355f10afa93','2026-08-31 16:21:31.545362'),(102,'4*2=','8','508658b30229700b9e590e4546e32ceb7bd59ab8','2026-08-31 16:22:25.861757'),(103,'8+1=','9','668a70b04b2a8e1f72c5d613e410d0f24ed7d27b','2026-08-31 16:23:23.511927'),(104,'2+5=','7','8bf605c68566569347d4417cf1c38ef30a5f7888','2026-08-31 16:25:36.420119'),(105,'6+7=','13','45c635d9279702decaecfc502c9e78d55ef1644c','2026-08-31 16:34:46.880687'),(106,'4+2=','6','bf2066dce19b6dd7e7959dda3a47adb6f6aa6a86','2026-08-31 16:39:10.969687'),(108,'9-1=','8','be481324775e6fd13facda8490b2b5204c3fa9ea','2026-08-31 17:45:55.148344'),(109,'3-3=','0','bf7ea98f7185b7e5af08922aab23636ca84d74c3','2026-08-31 17:51:49.013224'),(110,'2+4=','6','3419fd2b15b191fef210b7ccb8abc18813d8c84d','2026-08-31 18:14:05.756948'),(111,'10+1=','11','5a7aa7121c25d44fbf80c465a956dfee5caa922e','2026-08-31 18:15:45.609810'),(112,'4-1=','3','32288483174167b0542c9564b2343e56db818ff3','2026-08-31 18:19:47.561577'),(113,'9-3=','6','bab61ef6dae2c3d85d6f52f2237eba40d2b5c0a8','2026-08-31 18:20:44.384146'),(114,'5-1=','4','00b86a90504239c273007ce2869bcee190d9657e','2026-08-31 18:29:27.400668'),(115,'4*2=','8','0add39e2d904e412667a3234084d686964e9ed78','2026-08-31 18:42:53.809482');
/*!40000 ALTER TABLE `captcha_captchastore` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cmdb_business_line`
--

DROP TABLE IF EXISTS `cmdb_business_line`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmdb_business_line` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `code` varchar(32) DEFAULT NULL,
  `owner` varchar(64) DEFAULT NULL,
  `sort` int DEFAULT NULL,
  `status` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cmdb_business_line_creator_id_a95787fd` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cmdb_business_line`
--

LOCK TABLES `cmdb_business_line` WRITE;
/*!40000 ALTER TABLE `cmdb_business_line` DISABLE KEYS */;
INSERT INTO `cmdb_business_line` VALUES (1,NULL,NULL,NULL,'2026-08-28 09:35:55.977508','2026-08-28 09:35:55.977521','devops','devops',NULL,1,1,NULL);
/*!40000 ALTER TABLE `cmdb_business_line` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cmdb_environment`
--

DROP TABLE IF EXISTS `cmdb_environment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmdb_environment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `code` varchar(32) DEFAULT NULL,
  `sort` int DEFAULT NULL,
  `status` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cmdb_environment_creator_id_623d474a` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cmdb_environment`
--

LOCK TABLES `cmdb_environment` WRITE;
/*!40000 ALTER TABLE `cmdb_environment` DISABLE KEYS */;
INSERT INTO `cmdb_environment` VALUES (1,NULL,NULL,NULL,'2026-08-28 09:35:55.967007','2026-08-28 09:35:55.967024','生产','prod',1,1,NULL),(2,NULL,NULL,NULL,'2026-08-28 09:35:55.970810','2026-08-28 09:35:55.970820','测试','test',2,1,NULL),(3,NULL,NULL,NULL,'2026-08-28 09:35:55.973936','2026-08-28 09:35:55.973949','开发','dev',3,1,NULL);
/*!40000 ALTER TABLE `cmdb_environment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cmdb_idc`
--

DROP TABLE IF EXISTS `cmdb_idc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmdb_idc` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `code` varchar(32) DEFAULT NULL,
  `location` varchar(128) DEFAULT NULL,
  `sort` int DEFAULT NULL,
  `status` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cmdb_idc_creator_id_9344ff2c` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cmdb_idc`
--

LOCK TABLES `cmdb_idc` WRITE;
/*!40000 ALTER TABLE `cmdb_idc` DISABLE KEYS */;
INSERT INTO `cmdb_idc` VALUES (1,NULL,NULL,NULL,'2026-08-28 09:35:55.980693','2026-08-28 09:35:55.980704','1号机房','idc1','1号机房',1,1,NULL),(3,NULL,'1','1','2026-08-28 09:59:13.819363','2026-08-28 09:59:13.819374','2号机房','idc2','2号机房',2,1,1);
/*!40000 ALTER TABLE `cmdb_idc` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cmdb_server`
--

DROP TABLE IF EXISTS `cmdb_server`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmdb_server` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `hostname` varchar(64) NOT NULL,
  `ip` varchar(64) NOT NULL,
  `extra_ips` varchar(255) DEFAULT NULL,
  `os` varchar(128) DEFAULT NULL,
  `cpu` int DEFAULT NULL,
  `memory` int DEFAULT NULL,
  `disk` varchar(255) DEFAULT NULL,
  `deploy_content` varchar(255) DEFAULT NULL,
  `serial_number` varchar(64) DEFAULT NULL,
  `purchase_date` date DEFAULT NULL,
  `warranty_expiry` date DEFAULT NULL,
  `ssh_port` int NOT NULL,
  `status` varchar(20) NOT NULL,
  `tags` varchar(255) DEFAULT NULL,
  `business_line_id` bigint DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `environment_id` bigint DEFAULT NULL,
  `idc_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cmdb_server_ip_051f54e8` (`ip`),
  KEY `cmdb_server_business_line_id_607af763` (`business_line_id`),
  KEY `cmdb_server_creator_id_b0cde0a6` (`creator_id`),
  KEY `cmdb_server_environment_id_5d59f96a` (`environment_id`),
  KEY `cmdb_server_idc_id_9437a249` (`idc_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cmdb_server`
--

LOCK TABLES `cmdb_server` WRITE;
/*!40000 ALTER TABLE `cmdb_server` DISABLE KEYS */;
INSERT INTO `cmdb_server` VALUES (1,NULL,'1','1','2026-08-28 12:32:31.704512','2026-08-28 12:32:31.704524','YOUR_SERVER_IP','YOUR_SERVER_IP',NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,22,'online',NULL,1,1,2,1);
/*!40000 ALTER TABLE `cmdb_server` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_clockedschedule`
--

DROP TABLE IF EXISTS `django_celery_beat_clockedschedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_clockedschedule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `clocked_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_clockedschedule`
--

LOCK TABLES `django_celery_beat_clockedschedule` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_clockedschedule` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_celery_beat_clockedschedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_crontabschedule`
--

DROP TABLE IF EXISTS `django_celery_beat_crontabschedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_crontabschedule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `minute` varchar(240) NOT NULL,
  `hour` varchar(96) NOT NULL,
  `day_of_week` varchar(64) NOT NULL,
  `day_of_month` varchar(124) NOT NULL,
  `month_of_year` varchar(64) NOT NULL,
  `timezone` varchar(63) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_crontabschedule`
--

LOCK TABLES `django_celery_beat_crontabschedule` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_crontabschedule` DISABLE KEYS */;
INSERT INTO `django_celery_beat_crontabschedule` VALUES (1,'0','4','*','*','*','Asia/Shanghai');
/*!40000 ALTER TABLE `django_celery_beat_crontabschedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_intervalschedule`
--

DROP TABLE IF EXISTS `django_celery_beat_intervalschedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_intervalschedule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `every` int NOT NULL,
  `period` varchar(24) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_intervalschedule`
--

LOCK TABLES `django_celery_beat_intervalschedule` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_intervalschedule` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_celery_beat_intervalschedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_periodictask`
--

DROP TABLE IF EXISTS `django_celery_beat_periodictask`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_periodictask` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `task` varchar(200) NOT NULL,
  `args` longtext NOT NULL,
  `kwargs` longtext NOT NULL,
  `queue` varchar(200) DEFAULT NULL,
  `exchange` varchar(200) DEFAULT NULL,
  `routing_key` varchar(200) DEFAULT NULL,
  `expires` datetime(6) DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL,
  `last_run_at` datetime(6) DEFAULT NULL,
  `total_run_count` int unsigned NOT NULL,
  `date_changed` datetime(6) NOT NULL,
  `description` longtext NOT NULL,
  `crontab_id` int DEFAULT NULL,
  `interval_id` int DEFAULT NULL,
  `solar_id` int DEFAULT NULL,
  `one_off` tinyint(1) NOT NULL,
  `start_time` datetime(6) DEFAULT NULL,
  `priority` int unsigned DEFAULT NULL,
  `headers` longtext NOT NULL DEFAULT (_utf8'{}'),
  `clocked_id` int DEFAULT NULL,
  `expire_seconds` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `django_celery_beat_p_crontab_id_d3cba168_fk_django_ce` (`crontab_id`),
  KEY `django_celery_beat_p_interval_id_a8ca27da_fk_django_ce` (`interval_id`),
  KEY `django_celery_beat_p_solar_id_a87ce72c_fk_django_ce` (`solar_id`),
  KEY `django_celery_beat_p_clocked_id_47a69f82_fk_django_ce` (`clocked_id`),
  CONSTRAINT `django_celery_beat_p_clocked_id_47a69f82_fk_django_ce` FOREIGN KEY (`clocked_id`) REFERENCES `django_celery_beat_clockedschedule` (`id`),
  CONSTRAINT `django_celery_beat_p_crontab_id_d3cba168_fk_django_ce` FOREIGN KEY (`crontab_id`) REFERENCES `django_celery_beat_crontabschedule` (`id`),
  CONSTRAINT `django_celery_beat_p_interval_id_a8ca27da_fk_django_ce` FOREIGN KEY (`interval_id`) REFERENCES `django_celery_beat_intervalschedule` (`id`),
  CONSTRAINT `django_celery_beat_p_solar_id_a87ce72c_fk_django_ce` FOREIGN KEY (`solar_id`) REFERENCES `django_celery_beat_solarschedule` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_periodictask`
--

LOCK TABLES `django_celery_beat_periodictask` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_periodictask` DISABLE KEYS */;
INSERT INTO `django_celery_beat_periodictask` VALUES (1,'celery.backend_cleanup','celery.backend_cleanup','[]','{}',NULL,NULL,NULL,NULL,1,'2026-08-31 20:00:00.000309',3,'2026-09-01 04:01:35.044020','',1,NULL,NULL,0,NULL,NULL,'{}',NULL,43200);
/*!40000 ALTER TABLE `django_celery_beat_periodictask` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_periodictasks`
--

DROP TABLE IF EXISTS `django_celery_beat_periodictasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_periodictasks` (
  `ident` smallint NOT NULL,
  `last_update` datetime(6) NOT NULL,
  PRIMARY KEY (`ident`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_periodictasks`
--

LOCK TABLES `django_celery_beat_periodictasks` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_periodictasks` DISABLE KEYS */;
INSERT INTO `django_celery_beat_periodictasks` VALUES (1,'2026-08-31 08:34:05.207725');
/*!40000 ALTER TABLE `django_celery_beat_periodictasks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_beat_solarschedule`
--

DROP TABLE IF EXISTS `django_celery_beat_solarschedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_beat_solarschedule` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event` varchar(24) NOT NULL,
  `latitude` decimal(9,6) NOT NULL,
  `longitude` decimal(9,6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq` (`event`,`latitude`,`longitude`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_beat_solarschedule`
--

LOCK TABLES `django_celery_beat_solarschedule` WRITE;
/*!40000 ALTER TABLE `django_celery_beat_solarschedule` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_celery_beat_solarschedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_results_chordcounter`
--

DROP TABLE IF EXISTS `django_celery_results_chordcounter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_results_chordcounter` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` varchar(255) NOT NULL,
  `sub_tasks` longtext NOT NULL,
  `count` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `group_id` (`group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_results_chordcounter`
--

LOCK TABLES `django_celery_results_chordcounter` WRITE;
/*!40000 ALTER TABLE `django_celery_results_chordcounter` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_celery_results_chordcounter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_results_groupresult`
--

DROP TABLE IF EXISTS `django_celery_results_groupresult`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_results_groupresult` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` varchar(255) NOT NULL,
  `date_created` datetime(6) NOT NULL,
  `date_done` datetime(6) NOT NULL,
  `content_type` varchar(128) NOT NULL,
  `content_encoding` varchar(64) NOT NULL,
  `result` longtext,
  PRIMARY KEY (`id`),
  UNIQUE KEY `group_id` (`group_id`),
  KEY `django_cele_date_cr_bd6c1d_idx` (`date_created`),
  KEY `django_cele_date_do_caae0e_idx` (`date_done`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_results_groupresult`
--

LOCK TABLES `django_celery_results_groupresult` WRITE;
/*!40000 ALTER TABLE `django_celery_results_groupresult` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_celery_results_groupresult` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_celery_results_taskresult`
--

DROP TABLE IF EXISTS `django_celery_results_taskresult`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_celery_results_taskresult` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` varchar(255) NOT NULL,
  `periodic_task_name` varchar(255) DEFAULT NULL,
  `task_name` varchar(255) DEFAULT NULL,
  `task_args` longtext,
  `task_kwargs` longtext,
  `status` varchar(50) NOT NULL,
  `worker` varchar(100) DEFAULT NULL,
  `content_type` varchar(128) NOT NULL,
  `content_encoding` varchar(64) NOT NULL,
  `result` longtext,
  `date_created` datetime(6) NOT NULL,
  `date_done` datetime(6) NOT NULL,
  `traceback` longtext,
  `meta` longtext,
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_id` (`task_id`),
  KEY `django_cele_task_na_08aec9_idx` (`task_name`),
  KEY `django_cele_status_9b6201_idx` (`status`),
  KEY `django_cele_worker_d54dd8_idx` (`worker`),
  KEY `django_cele_date_cr_f04a50_idx` (`date_created`),
  KEY `django_cele_date_do_f59aad_idx` (`date_done`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_celery_results_taskresult`
--

LOCK TABLES `django_celery_results_taskresult` WRITE;
/*!40000 ALTER TABLE `django_celery_results_taskresult` DISABLE KEYS */;
INSERT INTO `django_celery_results_taskresult` VALUES (2,'5a540f17-1648-4eb0-b48b-ecb763a210a1','celery.backend_cleanup','celery.backend_cleanup','\"()\"','\"{}\"','SUCCESS','celery@85b14ae4f2d7','application/json','utf-8','null','2026-08-31 08:34:06.519051','2026-08-31 08:34:06.519060',NULL,'{\"children\": []}'),(3,'d22a4687-5e7c-4e9b-8220-76467659e532','celery.backend_cleanup','celery.backend_cleanup','\"()\"','\"{}\"','SUCCESS','celery@85b14ae4f2d7','application/json','utf-8','null','2026-09-01 04:00:00.009568','2026-09-01 04:00:00.009576',NULL,'{\"children\": []}');
/*!40000 ALTER TABLE `django_celery_results_taskresult` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (50,'alert','alertevent'),(47,'alert','alertgroup'),(45,'alert','alertrule'),(51,'alert','alerttemplate'),(46,'alert','notifychannel'),(2,'auth','group'),(1,'auth','permission'),(49,'bastion','commanddispatch'),(48,'bastion','commanddispatchitem'),(43,'bastion','commandlog'),(42,'bastion','credential'),(41,'bastion','sessionrecord'),(5,'captcha','captchastore'),(37,'cmdb','businessline'),(40,'cmdb','environment'),(38,'cmdb','idc'),(39,'cmdb','server'),(3,'contenttypes','contenttype'),(33,'django_celery_beat','clockedschedule'),(28,'django_celery_beat','crontabschedule'),(29,'django_celery_beat','intervalschedule'),(30,'django_celery_beat','periodictask'),(31,'django_celery_beat','periodictasks'),(32,'django_celery_beat','solarschedule'),(34,'django_celery_results','chordcounter'),(36,'django_celery_results','groupresult'),(35,'django_celery_results','taskresult'),(44,'monitor','prometheussource'),(4,'sessions','session'),(24,'system','apiwhitelist'),(23,'system','area'),(7,'system','dept'),(22,'system','dictionary'),(21,'system','downloadcenter'),(20,'system','fieldpermission'),(19,'system','filelist'),(18,'system','loginlog'),(8,'system','menu'),(9,'system','menubutton'),(17,'system','menufield'),(10,'system','messagecenter'),(16,'system','messagecentertargetuser'),(15,'system','operationlog'),(14,'system','post'),(11,'system','role'),(13,'system','rolemenubuttonpermission'),(12,'system','rolemenupermission'),(25,'system','systemconfig'),(6,'system','users'),(26,'test_app','blog'),(27,'test_app','product');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-08-27 18:04:33.859099'),(2,'contenttypes','0002_remove_content_type_name','2026-08-27 18:04:33.927076'),(3,'auth','0001_initial','2026-08-27 18:04:34.139257'),(4,'auth','0002_alter_permission_name_max_length','2026-08-27 18:04:34.186282'),(5,'auth','0003_alter_user_email_max_length','2026-08-27 18:04:34.191766'),(6,'auth','0004_alter_user_username_opts','2026-08-27 18:04:34.196544'),(7,'auth','0005_alter_user_last_login_null','2026-08-27 18:04:34.201329'),(8,'auth','0006_require_contenttypes_0002','2026-08-27 18:04:34.204130'),(9,'auth','0007_alter_validators_add_error_messages','2026-08-27 18:04:34.208340'),(10,'auth','0008_alter_user_username_max_length','2026-08-27 18:04:34.213891'),(11,'auth','0009_alter_user_last_name_max_length','2026-08-27 18:04:34.218798'),(12,'auth','0010_alter_group_name_max_length','2026-08-27 18:04:34.262353'),(13,'auth','0011_update_proxy_permissions','2026-08-27 18:04:34.268597'),(14,'auth','0012_alter_user_first_name_max_length','2026-08-27 18:04:34.273333'),(15,'captcha','0001_initial','2026-08-27 18:04:34.295351'),(16,'captcha','0002_alter_captchastore_id','2026-08-27 18:04:34.299153'),(17,'django_celery_beat','0001_initial','2026-08-27 18:04:34.465202'),(18,'django_celery_beat','0002_auto_20161118_0346','2026-08-27 18:04:34.564057'),(19,'django_celery_beat','0003_auto_20161209_0049','2026-08-27 18:04:34.584728'),(20,'django_celery_beat','0004_auto_20170221_0000','2026-08-27 18:04:34.589133'),(21,'django_celery_beat','0005_add_solarschedule_events_choices','2026-08-27 18:04:34.593283'),(22,'django_celery_beat','0006_auto_20180322_0932','2026-08-27 18:04:34.766126'),(23,'django_celery_beat','0007_auto_20180521_0826','2026-08-27 18:04:34.868955'),(24,'django_celery_beat','0008_auto_20180914_1922','2026-08-27 18:04:34.889747'),(25,'django_celery_beat','0006_auto_20180210_1226','2026-08-27 18:04:34.904354'),(26,'django_celery_beat','0006_periodictask_priority','2026-08-27 18:04:34.968210'),(27,'django_celery_beat','0009_periodictask_headers','2026-08-27 18:04:35.029838'),(28,'django_celery_beat','0010_auto_20190429_0326','2026-08-27 18:04:35.142183'),(29,'django_celery_beat','0011_auto_20190508_0153','2026-08-27 18:04:35.226340'),(30,'django_celery_beat','0012_periodictask_expire_seconds','2026-08-27 18:04:35.293449'),(31,'django_celery_beat','0013_auto_20200609_0727','2026-08-27 18:04:35.303583'),(32,'django_celery_beat','0014_remove_clockedschedule_enabled','2026-08-27 18:04:35.339179'),(33,'django_celery_beat','0015_edit_solarschedule_events_choices','2026-08-27 18:04:35.343670'),(34,'django_celery_beat','0016_alter_crontabschedule_timezone','2026-08-27 18:04:35.352775'),(35,'django_celery_beat','0017_alter_crontabschedule_month_of_year','2026-08-27 18:04:35.359295'),(36,'django_celery_beat','0018_improve_crontab_helptext','2026-08-27 18:04:35.366528'),(37,'django_celery_beat','0019_alter_periodictasks_options','2026-08-27 18:04:35.370115'),(38,'django_celery_results','0001_initial','2026-08-27 18:04:35.519058'),(39,'sessions','0001_initial','2026-08-27 18:04:35.550687'),(40,'system','0001_add_users_language','2026-08-27 18:04:37.252385'),(41,'system','0002_menu_name_en_menu_name_zh_tw_menubutton_name_en_and_more','2026-08-27 18:04:37.670454'),(42,'cmdb','0001_initial','2026-08-28 09:35:54.830915'),(43,'bastion','0001_initial','2026-08-28 11:54:08.035815'),(44,'monitor','0001_initial','2026-08-28 16:40:37.108040'),(45,'alert','0001_initial','2026-08-28 17:21:15.504369'),(46,'alert','0002_notifychannel','2026-08-28 17:46:35.180778'),(47,'alert','0003_alertgroup_alertrule_group','2026-08-28 18:08:18.292184'),(48,'bastion','0002_commanddispatch_commanddispatchitem','2026-08-31 11:27:21.573558'),(49,'bastion','0003_commanddispatch_max_workers_commandlog_dispatch_and_more','2026-08-31 13:49:27.864203'),(50,'bastion','0004_commanddispatchitem_ssh_port','2026-08-31 14:10:36.076932'),(51,'alert','0004_alter_notifychannel_config_alertevent','2026-08-31 15:12:00.677939'),(52,'alert','0005_alerttemplate','2026-08-31 15:52:20.052067'),(53,'alert','0006_remove_alerttemplate_rule_alertrule_template_and_more','2026-08-31 17:40:02.654972');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_api_white_list`
--

DROP TABLE IF EXISTS `dvadmin_api_white_list`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_api_white_list` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `url` varchar(200) NOT NULL,
  `method` int DEFAULT NULL,
  `enable_datasource` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_api_white_list_creator_id_fd335789` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_api_white_list`
--

LOCK TABLES `dvadmin_api_white_list` WRITE;
/*!40000 ALTER TABLE `dvadmin_api_white_list` DISABLE KEYS */;
INSERT INTO `dvadmin_api_white_list` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:39.985914','2026-08-27 18:04:39.985927','/api/system/dept_lazy_tree/',0,1,NULL);
/*!40000 ALTER TABLE `dvadmin_api_white_list` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_download_center`
--

DROP TABLE IF EXISTS `dvadmin_download_center`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_download_center` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `task_name` varchar(255) NOT NULL,
  `task_status` smallint NOT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `url` varchar(100) DEFAULT NULL,
  `size` bigint NOT NULL,
  `md5sum` varchar(36) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_download_center_creator_id_4a0a9256` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_download_center`
--

LOCK TABLES `dvadmin_download_center` WRITE;
/*!40000 ALTER TABLE `dvadmin_download_center` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_download_center` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_message_center`
--

DROP TABLE IF EXISTS `dvadmin_message_center`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_message_center` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `title` varchar(100) NOT NULL,
  `content` longtext NOT NULL,
  `target_type` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_message_center_creator_id_60e2080e` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_message_center`
--

LOCK TABLES `dvadmin_message_center` WRITE;
/*!40000 ALTER TABLE `dvadmin_message_center` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_message_center` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_message_center_target_dept`
--

DROP TABLE IF EXISTS `dvadmin_message_center_target_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_message_center_target_dept` (
  `id` int NOT NULL AUTO_INCREMENT,
  `messagecenter_id` bigint NOT NULL,
  `dept_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_message_center_t_messagecenter_id_dept_id_d9fb0c77_uniq` (`messagecenter_id`,`dept_id`),
  KEY `dvadmin_message_center_target_dept_messagecenter_id_69868c17` (`messagecenter_id`),
  KEY `dvadmin_message_center_target_dept_dept_id_616decc4` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_message_center_target_dept`
--

LOCK TABLES `dvadmin_message_center_target_dept` WRITE;
/*!40000 ALTER TABLE `dvadmin_message_center_target_dept` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_message_center_target_dept` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_message_center_target_role`
--

DROP TABLE IF EXISTS `dvadmin_message_center_target_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_message_center_target_role` (
  `id` int NOT NULL AUTO_INCREMENT,
  `messagecenter_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_message_center_t_messagecenter_id_role_id_f5a77970_uniq` (`messagecenter_id`,`role_id`),
  KEY `dvadmin_message_center_target_role_messagecenter_id_41a7bd9d` (`messagecenter_id`),
  KEY `dvadmin_message_center_target_role_role_id_661a61bb` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_message_center_target_role`
--

LOCK TABLES `dvadmin_message_center_target_role` WRITE;
/*!40000 ALTER TABLE `dvadmin_message_center_target_role` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_message_center_target_role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_message_center_target_user`
--

DROP TABLE IF EXISTS `dvadmin_message_center_target_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_message_center_target_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `messagecenter_id` bigint NOT NULL,
  `users_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_message_center_target_user_creator_id_0a27a561` (`creator_id`),
  KEY `dvadmin_message_center_target_user_messagecenter_id_54f35bf8` (`messagecenter_id`),
  KEY `dvadmin_message_center_target_user_users_id_9ff81ff5` (`users_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_message_center_target_user`
--

LOCK TABLES `dvadmin_message_center_target_user` WRITE;
/*!40000 ALTER TABLE `dvadmin_message_center_target_user` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_message_center_target_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_role_menu_button_permission`
--

DROP TABLE IF EXISTS `dvadmin_role_menu_button_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_role_menu_button_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `data_range` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `menu_button_id` bigint DEFAULT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_role_menu_button_permission_creator_id_76e161e6` (`creator_id`),
  KEY `dvadmin_role_menu_button_permission_menu_button_id_e2fba687` (`menu_button_id`),
  KEY `dvadmin_role_menu_button_permission_role_id_3b8dd37a` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=181 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_role_menu_button_permission`
--

LOCK TABLES `dvadmin_role_menu_button_permission` WRITE;
/*!40000 ALTER TABLE `dvadmin_role_menu_button_permission` DISABLE KEYS */;
INSERT INTO `dvadmin_role_menu_button_permission` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:39.980875','2026-08-27 18:04:39.980885',0,NULL,11,1),(2,NULL,NULL,NULL,'2026-08-28 15:17:43.030386','2026-08-28 15:17:43.030397',3,NULL,9,3),(3,NULL,NULL,NULL,'2026-08-28 15:17:43.033853','2026-08-28 15:17:43.033865',3,NULL,10,3),(4,NULL,NULL,NULL,'2026-08-28 15:17:43.037055','2026-08-28 15:17:43.037067',3,NULL,32,3),(5,NULL,NULL,NULL,'2026-08-28 15:17:43.040362','2026-08-28 15:17:43.040374',3,NULL,17,3),(6,NULL,NULL,NULL,'2026-08-28 15:17:43.043824','2026-08-28 15:17:43.043835',3,NULL,53,3),(7,NULL,NULL,NULL,'2026-08-28 15:17:43.047769','2026-08-28 15:17:43.047781',3,NULL,74,3),(8,NULL,NULL,NULL,'2026-08-28 15:17:43.051414','2026-08-28 15:17:43.051434',3,NULL,69,3),(9,NULL,NULL,NULL,'2026-08-28 15:17:43.055088','2026-08-28 15:17:43.055099',3,NULL,78,3),(10,NULL,NULL,NULL,'2026-08-28 15:17:43.058214','2026-08-28 15:17:43.058225',3,NULL,58,3),(11,NULL,NULL,NULL,'2026-08-28 15:17:43.061618','2026-08-28 15:17:43.061630',3,NULL,83,3),(12,NULL,NULL,NULL,'2026-08-28 15:17:43.064887','2026-08-28 15:17:43.064898',3,NULL,84,3),(13,NULL,NULL,NULL,'2026-08-28 15:17:43.068345','2026-08-28 15:17:43.068358',3,NULL,30,3),(14,NULL,NULL,NULL,'2026-08-28 15:17:43.071465','2026-08-28 15:17:43.071492',3,NULL,64,3),(15,NULL,NULL,NULL,'2026-08-28 15:17:43.074880','2026-08-28 15:17:43.074901',3,NULL,46,3),(16,NULL,NULL,NULL,'2026-08-28 15:17:43.078190','2026-08-28 15:17:43.078201',3,NULL,31,3),(17,NULL,NULL,NULL,'2026-08-28 15:17:43.082060','2026-08-28 15:17:43.082071',3,NULL,50,3),(18,NULL,NULL,NULL,'2026-08-28 15:17:43.084812','2026-08-28 15:17:43.084823',3,NULL,45,3),(19,NULL,NULL,NULL,'2026-08-28 15:17:43.088144','2026-08-28 15:17:43.088154',3,NULL,44,3),(20,NULL,NULL,NULL,'2026-08-28 15:17:43.091318','2026-08-28 15:17:43.091329',3,NULL,43,3),(21,NULL,NULL,NULL,'2026-08-28 15:17:43.096294','2026-08-28 15:17:43.096305',3,NULL,7,3),(22,NULL,NULL,NULL,'2026-08-28 15:17:43.099349','2026-08-28 15:17:43.099360',3,NULL,28,3),(23,NULL,NULL,NULL,'2026-08-28 15:17:43.102685','2026-08-28 15:17:43.102695',3,NULL,20,3),(24,NULL,NULL,NULL,'2026-08-28 15:17:43.106168','2026-08-28 15:17:43.106178',3,NULL,26,3),(25,NULL,NULL,NULL,'2026-08-28 15:17:43.109801','2026-08-28 15:17:43.109810',3,NULL,71,3),(26,NULL,NULL,NULL,'2026-08-28 15:17:43.113030','2026-08-28 15:17:43.113041',3,NULL,36,3),(27,NULL,NULL,NULL,'2026-08-28 15:17:43.116640','2026-08-28 15:17:43.116650',3,NULL,66,3),(28,NULL,NULL,NULL,'2026-08-28 15:17:43.120350','2026-08-28 15:17:43.120362',3,NULL,41,3),(29,NULL,NULL,NULL,'2026-08-28 15:17:43.123678','2026-08-28 15:17:43.123688',3,NULL,76,3),(30,NULL,NULL,NULL,'2026-08-28 15:17:43.126945','2026-08-28 15:17:43.126956',3,NULL,60,3),(31,NULL,NULL,NULL,'2026-08-28 15:17:43.131552','2026-08-28 15:17:43.131563',3,NULL,14,3),(32,NULL,NULL,NULL,'2026-08-28 15:17:43.134755','2026-08-28 15:17:43.134764',3,NULL,80,3),(33,NULL,NULL,NULL,'2026-08-28 15:17:43.137794','2026-08-28 15:17:43.137804',3,NULL,55,3),(34,NULL,NULL,NULL,'2026-08-28 15:17:43.141092','2026-08-28 15:17:43.141103',3,NULL,3,3),(35,NULL,NULL,NULL,'2026-08-28 15:17:43.145282','2026-08-28 15:17:43.145292',3,NULL,18,3),(36,NULL,NULL,NULL,'2026-08-28 15:17:43.148755','2026-08-28 15:17:43.148765',3,NULL,16,3),(37,NULL,NULL,NULL,'2026-08-28 15:17:43.152758','2026-08-28 15:17:43.152769',3,NULL,24,3),(38,NULL,NULL,NULL,'2026-08-28 15:17:43.156235','2026-08-28 15:17:43.156246',3,NULL,63,3),(39,NULL,NULL,NULL,'2026-08-28 15:17:43.159615','2026-08-28 15:17:43.159627',3,NULL,62,3),(40,NULL,NULL,NULL,'2026-08-28 15:17:43.162938','2026-08-28 15:17:43.162951',3,NULL,29,3),(41,NULL,NULL,NULL,'2026-08-28 15:17:43.166378','2026-08-28 15:17:43.166388',3,NULL,52,3),(42,NULL,NULL,NULL,'2026-08-28 15:17:43.169737','2026-08-28 15:17:43.169747',3,NULL,57,3),(43,NULL,NULL,NULL,'2026-08-28 15:17:43.173102','2026-08-28 15:17:43.173114',3,NULL,38,3),(44,NULL,NULL,NULL,'2026-08-28 15:17:43.176886','2026-08-28 15:17:43.176898',3,NULL,68,3),(45,NULL,NULL,NULL,'2026-08-28 15:17:43.179920','2026-08-28 15:17:43.179932',3,NULL,73,3),(46,NULL,NULL,NULL,'2026-08-28 15:17:43.183643','2026-08-28 15:17:43.183655',3,NULL,79,3),(47,NULL,NULL,NULL,'2026-08-28 15:17:43.187141','2026-08-28 15:17:43.187153',3,NULL,11,3),(48,NULL,NULL,NULL,'2026-08-28 15:17:43.190382','2026-08-28 15:17:43.190394',3,NULL,82,3),(49,NULL,NULL,NULL,'2026-08-28 15:17:43.194038','2026-08-28 15:17:43.194048',3,NULL,85,3),(50,NULL,NULL,NULL,'2026-08-28 15:17:43.197142','2026-08-28 15:17:43.197153',3,NULL,1,3),(51,NULL,NULL,NULL,'2026-08-28 15:17:43.200957','2026-08-28 15:17:43.200969',3,NULL,19,3),(52,NULL,NULL,NULL,'2026-08-28 15:17:43.203670','2026-08-28 15:17:43.203680',3,NULL,25,3),(53,NULL,NULL,NULL,'2026-08-28 15:17:43.207291','2026-08-28 15:17:43.207301',3,NULL,65,3),(54,NULL,NULL,NULL,'2026-08-28 15:17:43.211282','2026-08-28 15:17:43.211294',3,NULL,70,3),(55,NULL,NULL,NULL,'2026-08-28 15:17:43.214658','2026-08-28 15:17:43.214682',3,NULL,2,3),(56,NULL,NULL,NULL,'2026-08-28 15:17:43.218081','2026-08-28 15:17:43.218091',3,NULL,75,3),(57,NULL,NULL,NULL,'2026-08-28 15:17:43.221532','2026-08-28 15:17:43.221543',3,NULL,59,3),(58,NULL,NULL,NULL,'2026-08-28 15:17:43.224803','2026-08-28 15:17:43.224815',3,NULL,54,3),(59,NULL,NULL,NULL,'2026-08-28 15:17:43.228356','2026-08-28 15:17:43.228366',3,NULL,40,3),(60,NULL,NULL,NULL,'2026-08-28 15:17:43.232045','2026-08-28 15:17:43.232056',3,NULL,13,3),(61,NULL,NULL,NULL,'2026-08-28 15:17:43.235556','2026-08-28 15:17:43.235567',3,NULL,33,3),(62,NULL,NULL,NULL,'2026-08-28 15:17:43.239200','2026-08-28 15:17:43.239210',3,NULL,48,3),(63,NULL,NULL,NULL,'2026-08-28 15:17:43.242589','2026-08-28 15:17:43.242600',3,NULL,47,3),(64,NULL,NULL,NULL,'2026-08-28 15:17:43.245836','2026-08-28 15:17:43.245846',3,NULL,51,3),(65,NULL,NULL,NULL,'2026-08-28 15:17:43.249506','2026-08-28 15:17:43.249516',3,NULL,49,3),(66,NULL,NULL,NULL,'2026-08-28 15:17:43.253028','2026-08-28 15:17:43.253038',3,NULL,8,3),(67,NULL,NULL,NULL,'2026-08-28 15:17:43.256364','2026-08-28 15:17:43.256375',3,NULL,88,3),(68,NULL,NULL,NULL,'2026-08-28 15:17:43.259767','2026-08-28 15:17:43.259779',3,NULL,5,3),(69,NULL,NULL,NULL,'2026-08-28 15:17:43.262917','2026-08-28 15:17:43.262927',3,NULL,87,3),(70,NULL,NULL,NULL,'2026-08-28 15:17:43.266003','2026-08-28 15:17:43.266016',3,NULL,6,3),(71,NULL,NULL,NULL,'2026-08-28 15:17:43.269112','2026-08-28 15:17:43.269124',3,NULL,86,3),(72,NULL,NULL,NULL,'2026-08-28 15:17:43.273600','2026-08-28 15:17:43.273612',3,NULL,39,3),(73,NULL,NULL,NULL,'2026-08-28 15:17:43.276738','2026-08-28 15:17:43.276750',3,NULL,12,3),(74,NULL,NULL,NULL,'2026-08-28 15:17:43.279802','2026-08-28 15:17:43.279814',3,NULL,21,3),(75,NULL,NULL,NULL,'2026-08-28 15:17:43.283857','2026-08-28 15:17:43.283869',3,NULL,27,3),(76,NULL,NULL,NULL,'2026-08-28 15:17:43.287290','2026-08-28 15:17:43.287301',3,NULL,15,3),(77,NULL,NULL,NULL,'2026-08-28 15:17:43.290542','2026-08-28 15:17:43.290552',3,NULL,56,3),(78,NULL,NULL,NULL,'2026-08-28 15:17:43.293612','2026-08-28 15:17:43.293623',3,NULL,4,3),(79,NULL,NULL,NULL,'2026-08-28 15:17:43.296580','2026-08-28 15:17:43.296590',3,NULL,61,3),(80,NULL,NULL,NULL,'2026-08-28 15:17:43.300197','2026-08-28 15:17:43.300208',3,NULL,42,3),(81,NULL,NULL,NULL,'2026-08-28 15:17:43.303565','2026-08-28 15:17:43.303577',3,NULL,81,3),(82,NULL,NULL,NULL,'2026-08-28 15:17:43.306989','2026-08-28 15:17:43.307001',3,NULL,37,3),(83,NULL,NULL,NULL,'2026-08-28 15:17:43.310185','2026-08-28 15:17:43.310197',3,NULL,77,3),(84,NULL,NULL,NULL,'2026-08-28 15:17:43.313334','2026-08-28 15:17:43.313345',3,NULL,72,3),(85,NULL,NULL,NULL,'2026-08-28 15:17:43.316527','2026-08-28 15:17:43.316539',3,NULL,67,3),(86,NULL,NULL,NULL,'2026-08-28 15:17:43.319737','2026-08-28 15:17:43.319749',3,NULL,23,3),(87,NULL,NULL,NULL,'2026-08-28 15:17:43.323052','2026-08-28 15:17:43.323064',3,NULL,35,3),(88,NULL,NULL,NULL,'2026-08-28 15:17:43.327089','2026-08-28 15:17:43.327101',3,NULL,22,3),(89,NULL,NULL,NULL,'2026-08-28 15:17:43.330675','2026-08-28 15:17:43.330687',3,NULL,34,3),(90,NULL,NULL,NULL,'2026-08-28 15:42:24.121122','2026-08-28 15:42:24.121132',3,NULL,9,1),(91,NULL,NULL,NULL,'2026-08-28 15:42:24.124857','2026-08-28 15:42:24.124869',3,NULL,10,1),(92,NULL,NULL,NULL,'2026-08-28 15:42:24.127815','2026-08-28 15:42:24.127826',3,NULL,32,1),(93,NULL,NULL,NULL,'2026-08-28 15:42:24.130937','2026-08-28 15:42:24.130948',3,NULL,17,1),(94,NULL,NULL,NULL,'2026-08-28 15:42:24.134064','2026-08-28 15:42:24.134075',3,NULL,53,1),(95,NULL,NULL,NULL,'2026-08-28 15:42:24.137194','2026-08-28 15:42:24.137206',3,NULL,74,1),(96,NULL,NULL,NULL,'2026-08-28 15:42:24.141105','2026-08-28 15:42:24.141119',3,NULL,69,1),(97,NULL,NULL,NULL,'2026-08-28 15:42:24.145362','2026-08-28 15:42:24.145375',3,NULL,78,1),(98,NULL,NULL,NULL,'2026-08-28 15:42:24.148994','2026-08-28 15:42:24.149005',3,NULL,58,1),(99,NULL,NULL,NULL,'2026-08-28 15:42:24.152171','2026-08-28 15:42:24.152182',3,NULL,83,1),(100,NULL,NULL,NULL,'2026-08-28 15:42:24.155366','2026-08-28 15:42:24.155377',3,NULL,84,1),(101,NULL,NULL,NULL,'2026-08-28 15:42:24.158725','2026-08-28 15:42:24.158735',3,NULL,30,1),(102,NULL,NULL,NULL,'2026-08-28 15:42:24.162514','2026-08-28 15:42:24.162526',3,NULL,64,1),(103,NULL,NULL,NULL,'2026-08-28 15:42:24.168065','2026-08-28 15:42:24.168078',3,NULL,46,1),(104,NULL,NULL,NULL,'2026-08-28 15:42:24.172070','2026-08-28 15:42:24.172082',3,NULL,31,1),(105,NULL,NULL,NULL,'2026-08-28 15:42:24.174696','2026-08-28 15:42:24.174706',3,NULL,50,1),(106,NULL,NULL,NULL,'2026-08-28 15:42:24.177876','2026-08-28 15:42:24.177887',3,NULL,45,1),(107,NULL,NULL,NULL,'2026-08-28 15:42:24.181281','2026-08-28 15:42:24.181292',3,NULL,44,1),(108,NULL,NULL,NULL,'2026-08-28 15:42:24.184507','2026-08-28 15:42:24.184517',3,NULL,43,1),(109,NULL,NULL,NULL,'2026-08-28 15:42:24.187496','2026-08-28 15:42:24.187508',3,NULL,7,1),(110,NULL,NULL,NULL,'2026-08-28 15:42:24.190901','2026-08-28 15:42:24.190911',3,NULL,28,1),(111,NULL,NULL,NULL,'2026-08-28 15:42:24.194254','2026-08-28 15:42:24.194264',3,NULL,20,1),(112,NULL,NULL,NULL,'2026-08-28 15:42:24.197578','2026-08-28 15:42:24.197589',3,NULL,26,1),(113,NULL,NULL,NULL,'2026-08-28 15:42:24.200962','2026-08-28 15:42:24.200973',3,NULL,71,1),(114,NULL,NULL,NULL,'2026-08-28 15:42:24.204960','2026-08-28 15:42:24.204971',3,NULL,36,1),(115,NULL,NULL,NULL,'2026-08-28 15:42:24.219978','2026-08-28 15:42:24.219990',3,NULL,66,1),(116,NULL,NULL,NULL,'2026-08-28 15:42:24.223230','2026-08-28 15:42:24.223242',3,NULL,41,1),(117,NULL,NULL,NULL,'2026-08-28 15:42:24.227334','2026-08-28 15:42:24.227347',3,NULL,76,1),(118,NULL,NULL,NULL,'2026-08-28 15:42:24.231661','2026-08-28 15:42:24.231672',3,NULL,60,1),(119,NULL,NULL,NULL,'2026-08-28 15:42:24.234788','2026-08-28 15:42:24.234798',3,NULL,14,1),(120,NULL,NULL,NULL,'2026-08-28 15:42:24.238291','2026-08-28 15:42:24.238301',3,NULL,80,1),(121,NULL,NULL,NULL,'2026-08-28 15:42:24.241850','2026-08-28 15:42:24.241861',3,NULL,55,1),(122,NULL,NULL,NULL,'2026-08-28 15:42:24.244943','2026-08-28 15:42:24.244953',3,NULL,3,1),(123,NULL,NULL,NULL,'2026-08-28 15:42:24.248040','2026-08-28 15:42:24.248052',3,NULL,18,1),(124,NULL,NULL,NULL,'2026-08-28 15:42:24.251129','2026-08-28 15:42:24.251140',3,NULL,16,1),(125,NULL,NULL,NULL,'2026-08-28 15:42:24.254250','2026-08-28 15:42:24.254261',3,NULL,24,1),(126,NULL,NULL,NULL,'2026-08-28 15:42:24.257672','2026-08-28 15:42:24.257683',3,NULL,63,1),(127,NULL,NULL,NULL,'2026-08-28 15:42:24.260956','2026-08-28 15:42:24.260968',3,NULL,62,1),(128,NULL,NULL,NULL,'2026-08-28 15:42:24.264489','2026-08-28 15:42:24.264502',3,NULL,29,1),(129,NULL,NULL,NULL,'2026-08-28 15:42:24.267764','2026-08-28 15:42:24.267775',3,NULL,52,1),(130,NULL,NULL,NULL,'2026-08-28 15:42:24.272045','2026-08-28 15:42:24.272058',3,NULL,57,1),(131,NULL,NULL,NULL,'2026-08-28 15:42:24.275781','2026-08-28 15:42:24.275791',3,NULL,38,1),(132,NULL,NULL,NULL,'2026-08-28 15:42:24.278785','2026-08-28 15:42:24.278797',3,NULL,68,1),(133,NULL,NULL,NULL,'2026-08-28 15:42:24.282173','2026-08-28 15:42:24.282184',3,NULL,73,1),(134,NULL,NULL,NULL,'2026-08-28 15:42:24.285516','2026-08-28 15:42:24.285527',3,NULL,79,1),(135,NULL,NULL,NULL,'2026-08-28 15:42:24.290812','2026-08-28 15:42:24.290824',3,NULL,82,1),(136,NULL,NULL,NULL,'2026-08-28 15:42:24.294974','2026-08-28 15:42:24.294986',3,NULL,85,1),(137,NULL,NULL,NULL,'2026-08-28 15:42:24.298130','2026-08-28 15:42:24.298143',3,NULL,1,1),(138,NULL,NULL,NULL,'2026-08-28 15:42:24.301314','2026-08-28 15:42:24.301327',3,NULL,19,1),(139,NULL,NULL,NULL,'2026-08-28 15:42:24.304727','2026-08-28 15:42:24.304740',3,NULL,25,1),(140,NULL,NULL,NULL,'2026-08-28 15:42:24.308188','2026-08-28 15:42:24.308200',3,NULL,65,1),(141,NULL,NULL,NULL,'2026-08-28 15:42:24.311435','2026-08-28 15:42:24.311447',3,NULL,70,1),(142,NULL,NULL,NULL,'2026-08-28 15:42:24.314867','2026-08-28 15:42:24.314877',3,NULL,2,1),(143,NULL,NULL,NULL,'2026-08-28 15:42:24.318854','2026-08-28 15:42:24.318865',3,NULL,75,1),(144,NULL,NULL,NULL,'2026-08-28 15:42:24.322066','2026-08-28 15:42:24.322078',3,NULL,59,1),(145,NULL,NULL,NULL,'2026-08-28 15:42:24.325874','2026-08-28 15:42:24.325884',3,NULL,54,1),(146,NULL,NULL,NULL,'2026-08-28 15:42:24.328887','2026-08-28 15:42:24.328899',3,NULL,40,1),(147,NULL,NULL,NULL,'2026-08-28 15:42:24.332109','2026-08-28 15:42:24.332121',3,NULL,13,1),(148,NULL,NULL,NULL,'2026-08-28 15:42:24.335393','2026-08-28 15:42:24.335403',3,NULL,33,1),(149,NULL,NULL,NULL,'2026-08-28 15:42:24.338726','2026-08-28 15:42:24.338737',3,NULL,48,1),(150,NULL,NULL,NULL,'2026-08-28 15:42:24.342114','2026-08-28 15:42:24.342127',3,NULL,47,1),(151,NULL,NULL,NULL,'2026-08-28 15:42:24.345317','2026-08-28 15:42:24.345329',3,NULL,51,1),(152,NULL,NULL,NULL,'2026-08-28 15:42:24.348645','2026-08-28 15:42:24.348658',3,NULL,49,1),(153,NULL,NULL,NULL,'2026-08-28 15:42:24.351862','2026-08-28 15:42:24.351874',3,NULL,8,1),(154,NULL,NULL,NULL,'2026-08-28 15:42:24.355824','2026-08-28 15:42:24.355836',3,NULL,88,1),(155,NULL,NULL,NULL,'2026-08-28 15:42:24.359168','2026-08-28 15:42:24.359180',3,NULL,5,1),(156,NULL,NULL,NULL,'2026-08-28 15:42:24.362428','2026-08-28 15:42:24.362440',3,NULL,87,1),(157,NULL,NULL,NULL,'2026-08-28 15:42:24.365817','2026-08-28 15:42:24.365828',3,NULL,6,1),(158,NULL,NULL,NULL,'2026-08-28 15:42:24.369205','2026-08-28 15:42:24.369218',3,NULL,86,1),(159,NULL,NULL,NULL,'2026-08-28 15:42:24.372427','2026-08-28 15:42:24.372438',3,NULL,39,1),(160,NULL,NULL,NULL,'2026-08-28 15:42:24.376422','2026-08-28 15:42:24.376433',3,NULL,12,1),(161,NULL,NULL,NULL,'2026-08-28 15:42:24.379698','2026-08-28 15:42:24.379709',3,NULL,21,1),(162,NULL,NULL,NULL,'2026-08-28 15:42:24.383118','2026-08-28 15:42:24.383129',3,NULL,27,1),(163,NULL,NULL,NULL,'2026-08-28 15:42:24.386327','2026-08-28 15:42:24.386340',3,NULL,15,1),(164,NULL,NULL,NULL,'2026-08-28 15:42:24.389611','2026-08-28 15:42:24.389622',3,NULL,56,1),(165,NULL,NULL,NULL,'2026-08-28 15:42:24.392630','2026-08-28 15:42:24.392642',3,NULL,4,1),(166,NULL,NULL,NULL,'2026-08-28 15:42:24.396005','2026-08-28 15:42:24.396016',3,NULL,61,1),(167,NULL,NULL,NULL,'2026-08-28 15:42:24.399111','2026-08-28 15:42:24.399122',3,NULL,42,1),(168,NULL,NULL,NULL,'2026-08-28 15:42:24.402013','2026-08-28 15:42:24.402023',3,NULL,81,1),(169,NULL,NULL,NULL,'2026-08-28 15:42:24.404534','2026-08-28 15:42:24.404545',3,NULL,37,1),(170,NULL,NULL,NULL,'2026-08-28 15:42:24.408043','2026-08-28 15:42:24.408054',3,NULL,77,1),(171,NULL,NULL,NULL,'2026-08-28 15:42:24.411831','2026-08-28 15:42:24.411842',3,NULL,72,1),(172,NULL,NULL,NULL,'2026-08-28 15:42:24.414772','2026-08-28 15:42:24.414785',3,NULL,67,1),(173,NULL,NULL,NULL,'2026-08-28 15:42:24.418066','2026-08-28 15:42:24.418078',3,NULL,23,1),(174,NULL,NULL,NULL,'2026-08-28 15:42:24.421374','2026-08-28 15:42:24.421385',3,NULL,35,1),(175,NULL,NULL,NULL,'2026-08-28 15:42:24.424680','2026-08-28 15:42:24.424693',3,NULL,22,1),(176,NULL,NULL,NULL,'2026-08-28 15:42:24.427996','2026-08-28 15:42:24.428008',3,NULL,34,1),(177,NULL,NULL,NULL,'2026-08-31 13:50:46.208407','2026-08-31 13:50:46.208420',3,NULL,91,3),(178,NULL,NULL,NULL,'2026-08-31 13:50:46.211582','2026-08-31 13:50:46.211595',3,NULL,89,3),(179,NULL,NULL,NULL,'2026-08-31 13:50:46.214724','2026-08-31 13:50:46.214734',3,NULL,90,3),(180,NULL,NULL,NULL,'2026-08-31 13:50:46.217838','2026-08-31 13:50:46.217850',3,NULL,92,3);
/*!40000 ALTER TABLE `dvadmin_role_menu_button_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_role_menu_button_permission_dept`
--

DROP TABLE IF EXISTS `dvadmin_role_menu_button_permission_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_role_menu_button_permission_dept` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rolemenubuttonpermission_id` bigint NOT NULL,
  `dept_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_role_menu_button_rolemenubuttonpermission_e9ad3e96_uniq` (`rolemenubuttonpermission_id`,`dept_id`),
  KEY `dvadmin_role_menu_button_pe_rolemenubuttonpermission_id_d43fe932` (`rolemenubuttonpermission_id`),
  KEY `dvadmin_role_menu_button_permission_dept_dept_id_8b8ccd69` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_role_menu_button_permission_dept`
--

LOCK TABLES `dvadmin_role_menu_button_permission_dept` WRITE;
/*!40000 ALTER TABLE `dvadmin_role_menu_button_permission_dept` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_role_menu_button_permission_dept` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_role_menu_permission`
--

DROP TABLE IF EXISTS `dvadmin_role_menu_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_role_menu_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `menu_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_role_menu_permission_creator_id_c45cb075` (`creator_id`),
  KEY `dvadmin_role_menu_permission_menu_id_f6486ce5` (`menu_id`),
  KEY `dvadmin_role_menu_permission_role_id_9a3f9bee` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_role_menu_permission`
--

LOCK TABLES `dvadmin_role_menu_permission` WRITE;
/*!40000 ALTER TABLE `dvadmin_role_menu_permission` DISABLE KEYS */;
INSERT INTO `dvadmin_role_menu_permission` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:39.970743','2026-08-27 18:04:39.970753',NULL,1,1),(2,NULL,NULL,NULL,'2026-08-27 18:04:39.975386','2026-08-27 18:04:39.975396',NULL,3,1),(3,NULL,NULL,NULL,'2026-08-28 15:17:42.920365','2026-08-28 15:17:42.920377',NULL,10,3),(4,NULL,NULL,NULL,'2026-08-28 15:17:42.923801','2026-08-28 15:17:42.923812',NULL,2,3),(5,NULL,NULL,NULL,'2026-08-28 15:17:42.928715','2026-08-28 15:17:42.928735',NULL,28,3),(6,NULL,NULL,NULL,'2026-08-28 15:17:42.935166','2026-08-28 15:17:42.935177',NULL,23,3),(7,NULL,NULL,NULL,'2026-08-28 15:17:42.938577','2026-08-28 15:17:42.938588',NULL,18,3),(8,NULL,NULL,NULL,'2026-08-28 15:17:42.942338','2026-08-28 15:17:42.942348',NULL,15,3),(9,NULL,NULL,NULL,'2026-08-28 15:17:42.945925','2026-08-28 15:17:42.945938',NULL,11,3),(10,NULL,NULL,NULL,'2026-08-28 15:17:42.949462','2026-08-28 15:17:42.949489',NULL,1,3),(11,NULL,NULL,NULL,'2026-08-28 15:17:42.953271','2026-08-28 15:17:42.953283',NULL,9,3),(12,NULL,NULL,NULL,'2026-08-28 15:17:42.956985','2026-08-28 15:17:42.956996',NULL,29,3),(13,NULL,NULL,NULL,'2026-08-28 15:17:42.960281','2026-08-28 15:17:42.960292',NULL,12,3),(14,NULL,NULL,NULL,'2026-08-28 15:17:42.964893','2026-08-28 15:17:42.964906',NULL,24,3),(15,NULL,NULL,NULL,'2026-08-28 15:17:42.969886','2026-08-28 15:17:42.969897',NULL,16,3),(16,NULL,NULL,NULL,'2026-08-28 15:17:42.973033','2026-08-28 15:17:42.973045',NULL,3,3),(17,NULL,NULL,NULL,'2026-08-28 15:17:42.976251','2026-08-28 15:17:42.976262',NULL,22,3),(18,NULL,NULL,NULL,'2026-08-28 15:17:42.979574','2026-08-28 15:17:42.979586',NULL,19,3),(19,NULL,NULL,NULL,'2026-08-28 15:17:42.982859','2026-08-28 15:17:42.982869',NULL,30,3),(20,NULL,NULL,NULL,'2026-08-28 15:17:42.986278','2026-08-28 15:17:42.986288',NULL,27,3),(21,NULL,NULL,NULL,'2026-08-28 15:17:42.990356','2026-08-28 15:17:42.990366',NULL,25,3),(22,NULL,NULL,NULL,'2026-08-28 15:17:42.994032','2026-08-28 15:17:42.994044',NULL,4,3),(23,NULL,NULL,NULL,'2026-08-28 15:17:42.997123','2026-08-28 15:17:42.997135',NULL,14,3),(24,NULL,NULL,NULL,'2026-08-28 15:17:43.000397','2026-08-28 15:17:43.000409',NULL,13,3),(25,NULL,NULL,NULL,'2026-08-28 15:17:43.003730','2026-08-28 15:17:43.003740',NULL,5,3),(26,NULL,NULL,NULL,'2026-08-28 15:17:43.006928','2026-08-28 15:17:43.006938',NULL,26,3),(27,NULL,NULL,NULL,'2026-08-28 15:17:43.011396','2026-08-28 15:17:43.011406',NULL,17,3),(28,NULL,NULL,NULL,'2026-08-28 15:17:43.014578','2026-08-28 15:17:43.014591',NULL,6,3),(29,NULL,NULL,NULL,'2026-08-28 15:17:43.017899','2026-08-28 15:17:43.017913',NULL,7,3),(30,NULL,NULL,NULL,'2026-08-28 15:17:43.023706','2026-08-28 15:17:43.023717',NULL,8,3),(31,NULL,NULL,NULL,'2026-08-28 15:42:24.024602','2026-08-28 15:42:24.024623',NULL,10,1),(32,NULL,NULL,NULL,'2026-08-28 15:42:24.028458','2026-08-28 15:42:24.028469',NULL,2,1),(33,NULL,NULL,NULL,'2026-08-28 15:42:24.032752','2026-08-28 15:42:24.032763',NULL,28,1),(34,NULL,NULL,NULL,'2026-08-28 15:42:24.036098','2026-08-28 15:42:24.036111',NULL,23,1),(35,NULL,NULL,NULL,'2026-08-28 15:42:24.039163','2026-08-28 15:42:24.039174',NULL,18,1),(36,NULL,NULL,NULL,'2026-08-28 15:42:24.042556','2026-08-28 15:42:24.042569',NULL,15,1),(37,NULL,NULL,NULL,'2026-08-28 15:42:24.045824','2026-08-28 15:42:24.045835',NULL,11,1),(38,NULL,NULL,NULL,'2026-08-28 15:42:24.053612','2026-08-28 15:42:24.053625',NULL,9,1),(39,NULL,NULL,NULL,'2026-08-28 15:42:24.056896','2026-08-28 15:42:24.056909',NULL,29,1),(40,NULL,NULL,NULL,'2026-08-28 15:42:24.060486','2026-08-28 15:42:24.060499',NULL,12,1),(41,NULL,NULL,NULL,'2026-08-28 15:42:24.064281','2026-08-28 15:42:24.064293',NULL,24,1),(42,NULL,NULL,NULL,'2026-08-28 15:42:24.067832','2026-08-28 15:42:24.067843',NULL,16,1),(43,NULL,NULL,NULL,'2026-08-28 15:42:24.071737','2026-08-28 15:42:24.071750',NULL,22,1),(44,NULL,NULL,NULL,'2026-08-28 15:42:24.074796','2026-08-28 15:42:24.074809',NULL,19,1),(45,NULL,NULL,NULL,'2026-08-28 15:42:24.078166','2026-08-28 15:42:24.078177',NULL,30,1),(46,NULL,NULL,NULL,'2026-08-28 15:42:24.082157','2026-08-28 15:42:24.082169',NULL,27,1),(47,NULL,NULL,NULL,'2026-08-28 15:42:24.084865','2026-08-28 15:42:24.084876',NULL,25,1),(48,NULL,NULL,NULL,'2026-08-28 15:42:24.087812','2026-08-28 15:42:24.087823',NULL,4,1),(49,NULL,NULL,NULL,'2026-08-28 15:42:24.091145','2026-08-28 15:42:24.091165',NULL,14,1),(50,NULL,NULL,NULL,'2026-08-28 15:42:24.094389','2026-08-28 15:42:24.094401',NULL,13,1),(51,NULL,NULL,NULL,'2026-08-28 15:42:24.097879','2026-08-28 15:42:24.097889',NULL,5,1),(52,NULL,NULL,NULL,'2026-08-28 15:42:24.102390','2026-08-28 15:42:24.102401',NULL,26,1),(53,NULL,NULL,NULL,'2026-08-28 15:42:24.105601','2026-08-28 15:42:24.105612',NULL,17,1),(54,NULL,NULL,NULL,'2026-08-28 15:42:24.108947','2026-08-28 15:42:24.108958',NULL,6,1),(55,NULL,NULL,NULL,'2026-08-28 15:42:24.112275','2026-08-28 15:42:24.112286',NULL,7,1),(56,NULL,NULL,NULL,'2026-08-28 15:42:24.115646','2026-08-28 15:42:24.115657',NULL,8,1),(57,NULL,NULL,NULL,'2026-08-28 16:43:29.011314','2026-08-28 16:43:29.011335',NULL,32,3),(58,NULL,NULL,NULL,'2026-08-28 16:43:29.017905','2026-08-28 16:43:29.017918',NULL,33,3),(59,NULL,NULL,NULL,'2026-08-28 16:43:29.030404','2026-08-28 16:43:29.030416',NULL,31,3),(60,NULL,NULL,NULL,'2026-08-28 17:25:21.142057','2026-08-28 17:25:21.142075',NULL,35,3),(61,NULL,NULL,NULL,'2026-08-28 17:25:21.159143','2026-08-28 17:25:21.159155',NULL,34,3),(62,NULL,NULL,NULL,'2026-08-31 11:29:05.200555','2026-08-31 11:29:05.200571',NULL,38,3);
/*!40000 ALTER TABLE `dvadmin_role_menu_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_area`
--

DROP TABLE IF EXISTS `dvadmin_system_area`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_area` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) NOT NULL,
  `level` bigint NOT NULL,
  `pinyin` varchar(255) NOT NULL,
  `initials` varchar(20) NOT NULL,
  `enable` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `pcode_id` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `dvadmin_system_area_creator_id_a5046ac0` (`creator_id`),
  KEY `dvadmin_system_area_pcode_id_f9b21462` (`pcode_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_area`
--

LOCK TABLES `dvadmin_system_area` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_area` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_area` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_config`
--

DROP TABLE IF EXISTS `dvadmin_system_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `title` varchar(50) NOT NULL,
  `key` varchar(100) NOT NULL,
  `value` json DEFAULT NULL,
  `sort` int NOT NULL,
  `status` tinyint(1) NOT NULL,
  `data_options` json DEFAULT NULL,
  `form_item_type` int NOT NULL,
  `rule` json DEFAULT NULL,
  `placeholder` varchar(50) DEFAULT NULL,
  `setting` json DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  `title_en` varchar(50) DEFAULT NULL,
  `title_zh_tw` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_config_key_parent_id_f8627867_uniq` (`key`,`parent_id`),
  KEY `dvadmin_system_config_key_473a4f8d` (`key`),
  KEY `dvadmin_system_config_creator_id_ba7fd60a` (`creator_id`),
  KEY `dvadmin_system_config_parent_id_1ff841b5` (`parent_id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_config`
--

LOCK TABLES `dvadmin_system_config` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_config` DISABLE KEYS */;
INSERT INTO `dvadmin_system_config` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:40.393212','2026-08-27 18:04:40.393224','基础配置','base',NULL,0,1,NULL,0,NULL,NULL,NULL,NULL,NULL,'Basic Config','基本配置'),(2,NULL,NULL,NULL,'2026-08-27 18:04:40.398422','2026-08-27 18:04:40.398433','网页标题','web_title','\"XwOps\"',1,1,NULL,0,'[]','请输入网站标题',NULL,NULL,1,'Web Title','網頁標題'),(3,NULL,NULL,NULL,'2026-08-27 18:04:40.403839','2026-08-27 18:04:40.403849','网站小图标','web_favicon','\"\"',1,1,NULL,0,'[]','请输入网站小图标',NULL,NULL,1,'Website Favicon','網站小圖示'),(4,NULL,'1',NULL,'2026-08-31 17:32:44.279852','2026-08-27 18:04:40.410257','开启验证码','captcha_state','true',1,1,NULL,9,'[{\"message\": \"必填项不能为空\", \"required\": true, \"message_en\": \"This field is required\", \"message_zh_tw\": \"必填項不能為空\"}]','请选择',NULL,NULL,1,'Enable Captcha','開啟驗證碼'),(5,NULL,NULL,NULL,'2026-08-27 18:04:40.415601','2026-08-27 18:04:40.415614','创建用户默认密码','default_password','\"YOUR_DEFAULT_PASSWORD\"',2,1,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": true, \"message_en\": \"This field is required\", \"message_zh_tw\": \"必填項不能為空\"}]','请输入默认密码',NULL,NULL,1,'Default Password','創建用戶默認密碼'),(6,NULL,NULL,NULL,'2026-08-27 18:04:40.421199','2026-08-27 18:04:40.421211','登录页配置','login',NULL,1,1,NULL,0,NULL,NULL,NULL,NULL,NULL,'Login Page Config','登錄頁配置'),(7,'系统名称',NULL,NULL,'2026-08-28 14:44:30.019043','2026-08-27 18:04:40.426263','网站标题','site_title','\"XwOps\"',1,1,NULL,0,'[]','请输入网站标题',NULL,NULL,6,'Site Title','網站標題'),(8,NULL,NULL,NULL,'2026-08-27 18:04:40.431224','2026-08-27 18:04:40.431235','网站名称','site_name','\"企业级DevOps平台\"',1,1,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": true, \"message_en\": \"This field is required\", \"message_zh_tw\": \"必填項不能為空\"}]','请输入网站名称',NULL,NULL,6,'Site Name','網站名稱'),(9,NULL,NULL,NULL,'2026-08-27 18:04:40.437181','2026-08-27 18:04:40.437192','登录网站Logo','site_logo',NULL,2,1,NULL,7,'[]','请上传网站Logo',NULL,NULL,6,'Login Logo','登錄網站Logo'),(10,NULL,NULL,NULL,'2026-08-27 18:04:40.442611','2026-08-27 18:04:40.442622','登录页背景图','login_background',NULL,3,1,NULL,7,'[]','请上传登录背景图',NULL,NULL,6,'Login Background','登錄頁背景圖'),(11,NULL,NULL,NULL,'2026-08-27 18:04:40.447893','2026-08-27 18:04:40.447904','版权信息','copyright','\"2024-2026 XwOps 所有权利保留\"',4,1,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": true, \"message_en\": \"This field is required\", \"message_zh_tw\": \"必填項不能為空\"}]','请输入版权信息',NULL,NULL,6,'Copyright','版權信息'),(12,NULL,NULL,NULL,'2026-08-27 18:04:40.453004','2026-08-27 18:04:40.453014','备案信息','keep_record','\"\"',5,1,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": true, \"message_en\": \"This field is required\", \"message_zh_tw\": \"必填項不能為空\"}]','请输入备案信息',NULL,NULL,6,'Filing Info','備案信息'),(13,NULL,'1',NULL,'2026-08-31 17:33:08.794014','2026-08-27 18:04:40.458075','帮助链接','help_url','\"https://django-vue-admin.com\"',6,1,NULL,0,'\"\"','请输入帮助链接',NULL,NULL,6,'Help Link','幫助連結'),(14,NULL,NULL,NULL,'2026-08-27 18:04:40.463438','2026-08-27 18:04:40.463448','隐私链接','privacy_url','\"/api/system/clause/privacy.html\"',7,1,NULL,0,'[]','请填写隐私链接',NULL,NULL,6,'Privacy Link','隱私連結'),(15,NULL,NULL,NULL,'2026-08-27 18:04:40.468295','2026-08-27 18:04:40.468306','条款链接','clause_url','\"/api/system/clause/terms_service.html\"',8,1,NULL,0,'[]','请输入条款链接',NULL,NULL,6,'Terms Link','條款連結'),(16,NULL,NULL,NULL,'2026-08-27 18:04:40.472649','2026-08-27 18:04:40.472659','文件存储配置','file_storage',NULL,0,1,NULL,0,NULL,NULL,NULL,NULL,NULL,'File Storage Config','文件存儲配置'),(17,NULL,NULL,NULL,'2026-08-27 18:04:40.477824','2026-08-27 18:04:40.477835','存储引擎','file_engine','\"local\"',1,1,NULL,4,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请选择存储引擎','\"file_engine\"',NULL,16,'Storage Engine','儲存引擎'),(18,NULL,NULL,NULL,'2026-08-27 18:04:40.483050','2026-08-27 18:04:40.483060','文件是否备份','file_backup','false',2,1,NULL,9,'[{\"message\": \"必填项不能为空\", \"required\": false}]','启用云存储时,文件是否备份到本地',NULL,NULL,16,'Backup Files','文件是否備份'),(19,NULL,NULL,NULL,'2026-08-27 18:04:40.488393','2026-08-27 18:04:40.488404','阿里云-AccessKey','aliyun_access_key',NULL,3,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入AccessKey',NULL,NULL,16,'Aliyun AccessKey','阿裡雲AccessKey'),(20,NULL,NULL,NULL,'2026-08-27 18:04:40.494924','2026-08-27 18:04:40.494934','阿里云-Secret','aliyun_access_secret',NULL,4,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入Secret',NULL,NULL,16,'Aliyun Secret','阿裡雲Secret'),(21,NULL,NULL,NULL,'2026-08-27 18:04:40.500609','2026-08-27 18:04:40.500620','阿里云-Endpoint','aliyun_endpoint',NULL,5,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入Endpoint',NULL,NULL,16,'Aliyun Endpoint','阿裡雲Endpoint'),(22,NULL,NULL,NULL,'2026-08-27 18:04:40.506238','2026-08-27 18:04:40.506250','阿里云-上传路径','aliyun_path','\"/media/\"',5,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入上传路径',NULL,NULL,16,'Aliyun Upload Path','阿裡雲上傳路徑'),(23,NULL,NULL,NULL,'2026-08-27 18:04:40.511303','2026-08-27 18:04:40.511313','阿里云-Bucket','aliyun_bucket',NULL,7,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入Bucket',NULL,NULL,16,'Aliyun Bucket','阿裡雲Bucket'),(24,NULL,NULL,NULL,'2026-08-27 18:04:40.516560','2026-08-27 18:04:40.516572','阿里云-CDN地址','aliyun_cdn_url',NULL,7,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入CDN地址',NULL,NULL,16,'Aliyun CDN URL','阿裡雲CDN位址'),(25,NULL,NULL,NULL,'2026-08-27 18:04:40.522637','2026-08-27 18:04:40.522647','腾讯云-SecretId','tencent_secret_id',NULL,8,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入SecretId',NULL,NULL,16,'Tencent SecretId','騰訊雲SecretId'),(26,NULL,NULL,NULL,'2026-08-27 18:04:40.527813','2026-08-27 18:04:40.527824','腾讯云-SecretKey','tencent_secret_key',NULL,9,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入SecretKey',NULL,NULL,16,'Tencent SecretKey','騰訊雲SecretKey'),(27,NULL,NULL,NULL,'2026-08-27 18:04:40.533079','2026-08-27 18:04:40.533089','腾讯云-Region','tencent_region',NULL,10,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入Region',NULL,NULL,16,'Tencent Region','騰訊雲Region'),(28,NULL,NULL,NULL,'2026-08-27 18:04:40.538694','2026-08-27 18:04:40.538705','腾讯云-Bucket','tencent_bucket',NULL,11,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入Bucket',NULL,NULL,16,'Tencent Bucket','騰訊雲Bucket'),(29,NULL,NULL,NULL,'2026-08-27 18:04:40.543527','2026-08-27 18:04:40.543536','腾讯云-上传路径','tencent_path','\"/media/\"',12,0,NULL,0,'[{\"message\": \"必填项不能为空\", \"required\": false}]','请输入上传路径',NULL,NULL,16,'Tencent Upload Path','騰訊雲上傳路徑');
/*!40000 ALTER TABLE `dvadmin_system_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_dept`
--

DROP TABLE IF EXISTS `dvadmin_system_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_dept` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `key` varchar(64) DEFAULT NULL,
  `sort` int NOT NULL,
  `owner` varchar(32) DEFAULT NULL,
  `phone` varchar(32) DEFAULT NULL,
  `email` varchar(32) DEFAULT NULL,
  `status` tinyint(1) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`),
  KEY `dvadmin_system_dept_creator_id_e69fd1ae` (`creator_id`),
  KEY `dvadmin_system_dept_parent_id_0f9eb419` (`parent_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_dept`
--

LOCK TABLES `dvadmin_system_dept` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_dept` DISABLE KEYS */;
INSERT INTO `dvadmin_system_dept` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:38.874037','2026-08-27 18:04:38.874054','DVAdmin团队','dvadmin',1,'','','',1,NULL,NULL),(2,NULL,NULL,NULL,'2026-08-27 18:04:38.878666','2026-08-27 18:04:38.878677','运营部','',2,'','','',1,NULL,1),(3,NULL,NULL,NULL,'2026-08-27 18:04:38.883991','2026-08-27 18:04:38.884002','技术部','technology',1,'','','',1,NULL,1);
/*!40000 ALTER TABLE `dvadmin_system_dept` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_dictionary`
--

DROP TABLE IF EXISTS `dvadmin_system_dictionary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_dictionary` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `label` varchar(100) DEFAULT NULL,
  `value` varchar(200) DEFAULT NULL,
  `type` int NOT NULL,
  `color` varchar(20) DEFAULT NULL,
  `is_value` tinyint(1) NOT NULL,
  `status` tinyint(1) NOT NULL,
  `sort` int DEFAULT NULL,
  `remark` varchar(2000) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_dictionary_creator_id_d1b44b9d` (`creator_id`),
  KEY `dvadmin_system_dictionary_parent_id_4cceb110` (`parent_id`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_dictionary`
--

LOCK TABLES `dvadmin_system_dictionary` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_dictionary` DISABLE KEYS */;
INSERT INTO `dvadmin_system_dictionary` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:39.990603','2026-08-27 18:04:39.990614','启用/禁用-布尔值','button_status_bool',0,NULL,0,1,1,NULL,NULL,NULL),(2,NULL,NULL,NULL,'2026-08-27 18:04:39.997417','2026-08-27 18:04:39.997428','启用','true',6,'success',1,1,1,NULL,NULL,1),(3,NULL,NULL,NULL,'2026-08-27 18:04:40.003793','2026-08-27 18:04:40.003806','禁用','false',6,'danger',1,1,2,NULL,NULL,1),(4,NULL,NULL,NULL,'2026-08-27 18:04:40.011405','2026-08-27 18:04:40.011417','系统按钮','system_button',0,NULL,0,1,2,NULL,NULL,NULL),(5,NULL,NULL,NULL,'2026-08-27 18:04:40.019498','2026-08-27 18:04:40.019510','新增','Create',0,'success',1,1,1,NULL,NULL,4),(6,NULL,NULL,NULL,'2026-08-27 18:04:40.025760','2026-08-27 18:04:40.025770','编辑','Update',0,'primary',1,1,2,NULL,NULL,4),(7,NULL,NULL,NULL,'2026-08-27 18:04:40.031746','2026-08-27 18:04:40.031757','删除','Delete',0,'danger',1,1,3,NULL,NULL,4),(8,NULL,NULL,NULL,'2026-08-27 18:04:40.037680','2026-08-27 18:04:40.037691','详情','Retrieve',0,'info',1,1,4,NULL,NULL,4),(9,NULL,NULL,NULL,'2026-08-27 18:04:40.043710','2026-08-27 18:04:40.043720','查询','Search',0,'warning',1,1,5,NULL,NULL,4),(10,NULL,NULL,NULL,'2026-08-27 18:04:40.049727','2026-08-27 18:04:40.049737','保存','Save',0,'success',1,1,6,NULL,NULL,4),(11,NULL,NULL,NULL,'2026-08-27 18:04:40.055808','2026-08-27 18:04:40.055818','导入','Import',0,'primary',1,1,7,NULL,NULL,4),(12,NULL,NULL,NULL,'2026-08-27 18:04:40.061969','2026-08-27 18:04:40.061980','导出','Export',0,'warning',1,1,8,NULL,NULL,4),(13,NULL,NULL,NULL,'2026-08-27 18:04:40.068176','2026-08-27 18:04:40.068187','启用/禁用-数字值','button_status_number',0,NULL,0,1,3,NULL,NULL,NULL),(14,NULL,NULL,NULL,'2026-08-27 18:04:40.075336','2026-08-27 18:04:40.075346','启用','1',1,'success',1,1,1,NULL,NULL,13),(15,NULL,NULL,NULL,'2026-08-27 18:04:40.085275','2026-08-27 18:04:40.085287','禁用','0',1,'danger',1,1,2,NULL,NULL,13),(16,NULL,NULL,NULL,'2026-08-27 18:04:40.091634','2026-08-27 18:04:40.091656','是/否-布尔值','button_whether_bool',0,NULL,0,1,4,NULL,NULL,NULL),(17,NULL,NULL,NULL,'2026-08-27 18:04:40.098847','2026-08-27 18:04:40.098859','是','true',6,'success',1,1,1,NULL,NULL,16),(18,NULL,NULL,NULL,'2026-08-27 18:04:40.106370','2026-08-27 18:04:40.106381','否','false',6,'danger',1,1,2,NULL,NULL,16),(19,NULL,NULL,NULL,'2026-08-27 18:04:40.113880','2026-08-27 18:04:40.113892','是/否-数字值','button_whether_number',0,NULL,0,1,5,NULL,NULL,NULL),(20,NULL,NULL,NULL,'2026-08-27 18:04:40.122487','2026-08-27 18:04:40.122501','是','1',1,'success',1,1,1,NULL,NULL,19),(21,NULL,NULL,NULL,'2026-08-27 18:04:40.129661','2026-08-27 18:04:40.129672','否','2',1,'danger',1,1,2,NULL,NULL,19),(22,NULL,NULL,NULL,'2026-08-27 18:04:40.136821','2026-08-27 18:04:40.136832','用户类型','user_type',0,NULL,0,1,6,NULL,NULL,NULL),(23,NULL,NULL,NULL,'2026-08-27 18:04:40.145738','2026-08-27 18:04:40.145749','后台用户','0',1,NULL,1,1,1,NULL,NULL,22),(24,NULL,NULL,NULL,'2026-08-27 18:04:40.153679','2026-08-27 18:04:40.153690','前台用户','1',1,NULL,1,1,2,NULL,NULL,22),(25,NULL,NULL,NULL,'2026-08-27 18:04:40.161054','2026-08-27 18:04:40.161065','表单类型','config_form_type',0,NULL,0,1,7,NULL,NULL,NULL),(26,NULL,NULL,NULL,'2026-08-27 18:04:40.170075','2026-08-27 18:04:40.170087','text','0',1,NULL,1,1,0,NULL,NULL,25),(27,NULL,NULL,NULL,'2026-08-27 18:04:40.179071','2026-08-27 18:04:40.179082','textarea','3',1,'',1,1,0,NULL,NULL,25),(28,NULL,NULL,NULL,'2026-08-27 18:04:40.188044','2026-08-27 18:04:40.188055','number','10',1,'',1,1,0,NULL,NULL,25),(29,NULL,NULL,NULL,'2026-08-27 18:04:40.196714','2026-08-27 18:04:40.196726','datetime','1',1,NULL,1,1,1,NULL,NULL,25),(30,NULL,NULL,NULL,'2026-08-27 18:04:40.206000','2026-08-27 18:04:40.206010','date','2',1,NULL,1,1,2,NULL,NULL,25),(31,NULL,NULL,NULL,'2026-08-27 18:04:40.214899','2026-08-27 18:04:40.214910','time','15',1,'',1,1,3,NULL,NULL,25),(32,NULL,NULL,NULL,'2026-08-27 18:04:40.223809','2026-08-27 18:04:40.223820','select','4',1,NULL,1,1,4,NULL,NULL,25),(33,NULL,NULL,NULL,'2026-08-27 18:04:40.232727','2026-08-27 18:04:40.232738','checkbox','5',1,NULL,1,1,5,NULL,NULL,25),(34,NULL,NULL,NULL,'2026-08-27 18:04:40.241636','2026-08-27 18:04:40.241647','radio','6',1,NULL,1,1,6,NULL,NULL,25),(35,NULL,NULL,NULL,'2026-08-27 18:04:40.250781','2026-08-27 18:04:40.250792','switch','9',1,'',1,1,6,NULL,NULL,25),(36,NULL,NULL,NULL,'2026-08-27 18:04:40.259708','2026-08-27 18:04:40.259718','文件附件','8',1,'',1,1,7,NULL,NULL,25),(37,NULL,NULL,NULL,'2026-08-27 18:04:40.268084','2026-08-27 18:04:40.268095','图片(单张)','7',1,'',1,1,8,NULL,NULL,25),(38,NULL,NULL,NULL,'2026-08-27 18:04:40.277528','2026-08-27 18:04:40.277540','图片(多张)','12',1,'',1,1,9,NULL,NULL,25),(39,NULL,NULL,NULL,'2026-08-27 18:04:40.286827','2026-08-27 18:04:40.286838','数组','11',1,'',1,1,11,NULL,NULL,25),(40,NULL,NULL,NULL,'2026-08-27 18:04:40.295807','2026-08-27 18:04:40.295817','关联表','13',1,'',1,1,13,NULL,NULL,25),(41,NULL,NULL,NULL,'2026-08-27 18:04:40.304762','2026-08-27 18:04:40.304773','关联表(多选)','14',1,'',1,1,14,NULL,NULL,25),(42,NULL,NULL,NULL,'2026-08-27 18:04:40.314122','2026-08-27 18:04:40.314133','性别','gender',0,NULL,0,1,8,NULL,NULL,NULL),(43,NULL,NULL,NULL,'2026-08-27 18:04:40.323840','2026-08-27 18:04:40.323851','未知','0',1,NULL,1,1,0,NULL,NULL,42),(44,NULL,NULL,NULL,'2026-08-27 18:04:40.333258','2026-08-27 18:04:40.333270','男','1',1,NULL,1,1,1,NULL,NULL,42),(45,NULL,NULL,NULL,'2026-08-27 18:04:40.343331','2026-08-27 18:04:40.343343','女','2',1,NULL,1,1,2,NULL,NULL,42),(46,NULL,NULL,NULL,'2026-08-27 18:04:40.352128','2026-08-27 18:04:40.352146','文件存储引擎','file_engine',0,NULL,0,1,9,NULL,NULL,NULL),(47,NULL,NULL,NULL,'2026-08-27 18:04:40.361396','2026-08-27 18:04:40.361408','本地','local',0,'primary',1,1,1,NULL,NULL,46),(48,NULL,NULL,NULL,'2026-08-27 18:04:40.371686','2026-08-27 18:04:40.371697','阿里云oss','oss',0,'success',1,1,2,NULL,NULL,46),(49,NULL,NULL,NULL,'2026-08-27 18:04:40.381954','2026-08-27 18:04:40.381965','腾讯cos','cos',0,'warning',1,1,3,NULL,NULL,46);
/*!40000 ALTER TABLE `dvadmin_system_dictionary` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_field_permission`
--

DROP TABLE IF EXISTS `dvadmin_system_field_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_field_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `is_query` tinyint(1) NOT NULL,
  `is_create` tinyint(1) NOT NULL,
  `is_update` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `field_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_field_permission_creator_id_44eb775e` (`creator_id`),
  KEY `dvadmin_system_field_permission_field_id_73711ad8` (`field_id`),
  KEY `dvadmin_system_field_permission_role_id_ef32fd10` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_field_permission`
--

LOCK TABLES `dvadmin_system_field_permission` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_field_permission` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_field_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_file_list`
--

DROP TABLE IF EXISTS `dvadmin_system_file_list`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_file_list` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(200) DEFAULT NULL,
  `url` varchar(100) DEFAULT NULL,
  `file_url` varchar(255) NOT NULL,
  `engine` varchar(100) NOT NULL,
  `mime_type` varchar(100) NOT NULL,
  `size` varchar(36) NOT NULL,
  `md5sum` varchar(36) NOT NULL,
  `upload_method` smallint DEFAULT NULL,
  `file_type` smallint DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_file_list_creator_id_dec6acb5` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_file_list`
--

LOCK TABLES `dvadmin_system_file_list` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_file_list` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_file_list` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_login_log`
--

DROP TABLE IF EXISTS `dvadmin_system_login_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_login_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `username` varchar(32) DEFAULT NULL,
  `ip` varchar(32) DEFAULT NULL,
  `agent` longtext,
  `browser` varchar(200) DEFAULT NULL,
  `os` varchar(200) DEFAULT NULL,
  `continent` varchar(50) DEFAULT NULL,
  `country` varchar(50) DEFAULT NULL,
  `province` varchar(50) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `district` varchar(50) DEFAULT NULL,
  `isp` varchar(50) DEFAULT NULL,
  `area_code` varchar(50) DEFAULT NULL,
  `country_english` varchar(50) DEFAULT NULL,
  `country_code` varchar(50) DEFAULT NULL,
  `longitude` varchar(50) DEFAULT NULL,
  `latitude` varchar(50) DEFAULT NULL,
  `login_type` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_login_log_creator_id_5f6dc165` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_login_log`
--

LOCK TABLES `dvadmin_system_login_log` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_login_log` DISABLE KEYS */;
INSERT INTO `dvadmin_system_login_log` VALUES (1,NULL,NULL,'1','2026-08-27 18:11:54.773895','2026-08-27 18:11:54.773917','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(2,NULL,NULL,'1','2026-08-28 09:57:58.464834','2026-08-28 09:57:58.464855','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(3,NULL,NULL,'1','2026-08-28 15:24:08.049690','2026-08-28 15:24:08.049712','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(4,NULL,NULL,'1','2026-08-28 15:25:31.124828','2026-08-28 15:25:31.124850','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(5,NULL,NULL,'1','2026-08-28 15:49:24.753562','2026-08-28 15:49:24.753584','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(6,NULL,NULL,'1','2026-08-28 15:59:27.361437','2026-08-28 15:59:27.361458','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(7,NULL,NULL,'1','2026-08-31 08:35:26.515289','2026-08-31 08:35:26.515310','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(8,NULL,NULL,'1','2026-08-31 13:22:15.708949','2026-08-31 13:22:15.708969','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(9,NULL,NULL,'1','2026-08-31 17:32:41.454841','2026-08-31 17:32:41.454868','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1),(10,NULL,NULL,'1','2026-09-01 08:25:03.101180','2026-09-01 08:25:03.101200','superadmin','127.0.0.1','PC / Windows 10 / Chrome 151.0.0','Chrome 151.0.0','Windows 10','亚洲','中国','安徽省','合肥市','','教育网','340100','China','CN','117.283042','31.86119',1,1);
/*!40000 ALTER TABLE `dvadmin_system_login_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_menu`
--

DROP TABLE IF EXISTS `dvadmin_system_menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_menu` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `icon` varchar(64) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `sort` int DEFAULT NULL,
  `is_link` tinyint(1) NOT NULL,
  `link_url` varchar(255) DEFAULT NULL,
  `is_catalog` tinyint(1) NOT NULL,
  `web_path` varchar(128) DEFAULT NULL,
  `component` varchar(128) DEFAULT NULL,
  `component_name` varchar(50) DEFAULT NULL,
  `status` tinyint(1) NOT NULL,
  `cache` tinyint(1) NOT NULL,
  `visible` tinyint(1) NOT NULL,
  `is_iframe` tinyint(1) NOT NULL,
  `is_affix` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  `name_en` varchar(64) DEFAULT NULL,
  `name_zh_tw` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_menu_creator_id_430cdc1c` (`creator_id`),
  KEY `dvadmin_system_menu_parent_id_bc6f21bc` (`parent_id`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_menu`
--

LOCK TABLES `dvadmin_system_menu` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_menu` DISABLE KEYS */;
INSERT INTO `dvadmin_system_menu` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:38.940620','2026-08-27 18:04:38.940631','iconfont icon-xitongshezhi','系统管理',1,0,NULL,1,'/system','','',1,0,1,0,0,NULL,NULL,'System Management','系統設置'),(2,NULL,NULL,NULL,'2026-08-27 18:04:38.945116','2026-08-27 18:04:38.945127','iconfont icon-icon-','用户管理',1,0,NULL,0,'/user','system/user/index','user',1,0,0,0,0,NULL,1,'User Management','用戶管理'),(3,NULL,NULL,NULL,'2026-08-27 18:04:39.058750','2026-08-27 18:04:39.058759','iconfont icon-caidan','菜单管理',2,0,NULL,0,'/menu','system/menu/index','menu',1,0,1,0,0,NULL,1,'Menu Management','選單管理'),(4,NULL,NULL,NULL,'2026-08-27 18:04:39.147233','2026-08-27 18:04:39.147244','ele-OfficeBuilding','架构管理',3,0,NULL,0,'/dept','system/dept/index','dept',1,0,1,0,0,NULL,1,'Department Management','部門管理'),(5,NULL,NULL,NULL,'2026-08-27 18:04:39.192376','2026-08-27 18:04:39.192386','ele-ColdDrink','角色管理',4,0,NULL,0,'/role','system/role/index','role',1,0,1,0,0,NULL,1,'Role Management','角色管理'),(6,NULL,NULL,NULL,'2026-08-27 18:04:39.303032','2026-08-27 18:04:39.303042','iconfont icon-xiaoxizhongxin','消息中心',7,0,NULL,0,'/messageCenter','system/messageCenter/index','messageCenter',1,0,1,0,0,NULL,1,'Notification Center','通知中心'),(7,NULL,NULL,NULL,'2026-08-27 18:04:39.371420','2026-08-27 18:04:39.371445','ele-SetUp','接口白名单',8,0,NULL,0,'/apiWhiteList','system/whiteList/index','whiteList',1,0,1,0,0,NULL,1,'API Whitelist','接口白名單'),(8,NULL,NULL,NULL,'2026-08-27 18:04:39.440350','2026-08-27 18:04:39.440362','ele-Download','下载中心',9,0,NULL,0,'/downloadCenter','system/downloadCenter/index','downloadCenter',1,0,1,0,0,NULL,1,'Download Center','下載中心'),(9,NULL,NULL,NULL,'2026-08-27 18:04:39.448789','2026-08-27 18:04:39.448800','iconfont icon-configure','常规配置',2,0,NULL,1,'/generalConfig','','',1,0,1,0,0,NULL,NULL,'General Config','常規配置'),(10,NULL,NULL,NULL,'2026-08-27 18:04:39.454247','2026-08-27 18:04:39.454257','iconfont icon-system','系统配置',0,0,NULL,0,'/config','system/config/index','config',1,0,1,0,0,NULL,9,'System Config','系統配置'),(11,NULL,NULL,NULL,'2026-08-27 18:04:39.482321','2026-08-27 18:04:39.482331','iconfont icon-dict','字典管理',1,0,NULL,0,'/dictionary','system/dictionary/index','dictionary',1,0,1,0,0,NULL,9,'Dictionary Management','字典管理'),(12,NULL,NULL,NULL,'2026-08-27 18:04:39.576972','2026-08-27 18:04:39.576986','iconfont icon-Area','地区管理',2,0,NULL,0,'/areas','system/areas/index','areas',1,0,1,0,0,NULL,9,'Area Management','地區管理'),(13,NULL,NULL,NULL,'2026-08-27 18:04:39.664321','2026-08-27 18:04:39.664332','iconfont icon-file','附件管理',3,0,NULL,0,'/file','system/fileList/index','file',1,0,1,0,0,NULL,9,'File Management','附件管理'),(14,NULL,NULL,NULL,'2026-08-27 18:04:39.749569','2026-08-27 18:04:39.749582','iconfont icon-rizhi','日志管理',3,0,NULL,1,'/log','','',1,0,1,0,0,NULL,NULL,'Log Management','日誌管理'),(15,NULL,NULL,NULL,'2026-08-27 18:04:39.754508','2026-08-27 18:04:39.754519','iconfont icon-guanlidenglurizhi','登录日志',1,0,NULL,0,'/loginLog','system/log/loginLog/index','loginLog',1,0,1,0,0,NULL,14,'Login Logs','登錄日誌'),(16,NULL,NULL,NULL,'2026-08-27 18:04:39.870522','2026-08-27 18:04:39.870534','iconfont icon-caozuorizhi','操作日志',2,0,NULL,0,'/operationLog','system/log/operationLog/index','operationLog',1,0,1,0,0,NULL,14,'Operation Logs','操作日誌'),(17,'','1',NULL,'2026-08-28 16:20:43.324931','2026-08-27 18:04:39.955170','iconfont icon-caijian','定时任务',6,0,NULL,1,'/celeryManage','','',1,1,1,0,0,NULL,NULL,'Scheduled Tasks','定時任務'),(18,NULL,NULL,NULL,'2026-08-28 16:01:43.800676','2026-08-27 18:04:39.959736','ele-Timer','任务管理',1,0,NULL,0,'/taskManage','celery/task/index','taskManage',1,0,1,0,0,NULL,17,'Task Management','任務管理'),(19,NULL,NULL,NULL,'2026-08-28 16:01:43.795896','2026-08-27 18:04:39.964374','ele-Memo','任务日志',2,0,NULL,0,'/taskLog','celery/taskLog/index','taskLog',1,0,1,0,0,NULL,17,'Task Logs','任務日誌'),(22,NULL,NULL,NULL,'2026-08-28 09:46:46.501192','2026-08-28 09:46:46.501213','ele-Folder','资产管理',2,0,NULL,1,'/cmdb',NULL,NULL,1,0,1,0,0,NULL,NULL,NULL,NULL),(23,NULL,NULL,NULL,'2026-08-28 09:46:46.505171','2026-08-28 09:46:46.505184','ele-OfficeBuilding','机房管理',1,0,NULL,0,'/idc','cmdb/idc/index','cmdbIdc',1,0,1,0,0,NULL,22,NULL,NULL),(24,NULL,NULL,NULL,'2026-08-28 09:46:46.508952','2026-08-28 09:46:46.508965','ele-SetUp','环境管理',2,0,NULL,0,'/environment','cmdb/environment/index','cmdbEnvironment',1,0,1,0,0,NULL,22,NULL,NULL),(25,NULL,NULL,NULL,'2026-08-28 09:46:46.511911','2026-08-28 09:46:46.511922','ele-Share','业务线管理',3,0,NULL,0,'/businessLine','cmdb/businessLine/index','cmdbBusinessLine',1,0,1,0,0,NULL,22,NULL,NULL),(26,NULL,NULL,NULL,'2026-08-28 09:46:46.514855','2026-08-28 09:46:46.514867','ele-Monitor','服务器管理',4,0,NULL,0,'/server','cmdb/server/index','cmdbServer',1,0,1,0,0,NULL,22,NULL,NULL),(27,NULL,NULL,NULL,'2026-08-28 12:01:24.013419','2026-08-28 12:01:24.013437','ele-Connection','堡垒机',3,0,NULL,1,'/bastion',NULL,NULL,1,0,1,0,0,NULL,NULL,NULL,NULL),(28,NULL,NULL,NULL,'2026-08-28 12:01:24.017517','2026-08-28 12:01:24.017529','ele-Key','凭据管理',1,0,NULL,0,'/credential','cmdb/credential/index','bastionCredential',1,0,1,0,0,NULL,27,NULL,NULL),(29,NULL,NULL,NULL,'2026-08-28 12:01:24.021256','2026-08-28 12:01:24.021274','ele-VideoPlay','会话记录',2,0,NULL,0,'/session','cmdb/session/index','bastionSession',1,0,1,0,0,NULL,27,NULL,NULL),(30,NULL,NULL,NULL,'2026-08-28 12:01:24.025304','2026-08-28 12:01:24.025314','ele-Document','命令审计',3,0,NULL,0,'/commandLog','cmdb/commandLog/index','bastionCommandLog',1,0,1,0,0,NULL,27,NULL,NULL),(31,NULL,NULL,NULL,'2026-08-28 16:43:03.926174','2026-08-28 16:43:03.926195','ele-Monitor','监控告警',4,0,NULL,1,'/monitor',NULL,NULL,1,0,1,0,0,NULL,NULL,NULL,NULL),(32,NULL,NULL,NULL,'2026-08-28 16:43:03.930906','2026-08-28 16:43:03.930917','ele-Cpu','数据源管理',1,0,NULL,0,'/source','monitor/source/index','monitorSource',1,0,1,0,0,NULL,31,NULL,NULL),(33,NULL,NULL,NULL,'2026-08-28 16:43:03.934648','2026-08-28 16:43:03.934659','ele-Search','指标查询',2,0,NULL,0,'/query','monitor/query/index','monitorQuery',1,0,1,0,0,NULL,31,NULL,NULL),(34,NULL,NULL,NULL,'2026-08-28 17:43:07.546620','2026-08-28 17:25:21.130337','ele-Bell','告警管理',3,0,NULL,1,'/alert',NULL,NULL,1,0,1,0,0,NULL,31,NULL,NULL),(35,NULL,NULL,NULL,'2026-08-31 15:18:32.038946','2026-08-28 17:25:21.134397','ele-AlarmClock','告警规则',2,0,NULL,0,'/rule','alert/rule/index','alertRule',1,0,1,0,0,NULL,34,NULL,NULL),(36,NULL,NULL,NULL,'2026-08-31 15:27:06.675323','2026-08-28 17:48:20.891287','ele-Connection','通知渠道',4,0,NULL,0,'/channel','alert/channel/index','alertChannel',1,0,1,0,0,NULL,34,NULL,NULL),(37,NULL,NULL,NULL,'2026-08-31 15:27:06.677937','2026-08-28 18:09:49.865500','ele-User','告警群组',5,0,NULL,0,'/group','alert/group/index','alertGroup',1,0,1,0,0,NULL,34,NULL,NULL),(38,NULL,NULL,NULL,'2026-08-31 11:29:05.192700','2026-08-31 11:29:05.192722','ele-Position','命令下发',4,0,NULL,0,'/dispatch','cmdb/commandDispatch/index',NULL,1,0,1,0,0,NULL,27,NULL,NULL),(39,NULL,NULL,NULL,'2026-08-31 15:18:09.574642','2026-08-31 15:18:09.574663','ele-Bell','活跃告警',1,0,NULL,0,'/alertManage','alert/manage/index','alertManage',1,0,1,0,0,NULL,34,NULL,NULL),(40,NULL,NULL,NULL,'2026-08-31 15:27:06.672489','2026-08-31 15:26:27.699392','ele-Document','历史告警',3,0,NULL,0,'/alertEvent','alert/event/index','alertEvent',1,0,1,0,0,NULL,34,NULL,NULL),(41,NULL,NULL,NULL,'2026-08-31 15:56:47.215010','2026-08-31 15:56:47.215031','ele-Document','告警模板',6,0,NULL,0,'/alertTemplate','alert/template/index','alertTemplate',1,0,1,0,0,NULL,34,NULL,NULL);
/*!40000 ALTER TABLE `dvadmin_system_menu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_menu_button`
--

DROP TABLE IF EXISTS `dvadmin_system_menu_button`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_menu_button` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `value` varchar(64) NOT NULL,
  `api` varchar(200) NOT NULL,
  `method` int DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `menu_id` bigint NOT NULL,
  `name_en` varchar(64) DEFAULT NULL,
  `name_zh_tw` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `value` (`value`),
  KEY `dvadmin_system_menu_button_creator_id_3df058f7` (`creator_id`),
  KEY `dvadmin_system_menu_button_menu_id_f6aafcd8` (`menu_id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_menu_button`
--

LOCK TABLES `dvadmin_system_menu_button` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_menu_button` DISABLE KEYS */;
INSERT INTO `dvadmin_system_menu_button` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:38.950202','2026-08-27 18:04:38.950212','查询','user:Search','/api/system/user/',0,NULL,2,'Search','查詢'),(2,NULL,NULL,NULL,'2026-08-27 18:04:38.954836','2026-08-27 18:04:38.954858','新增','user:Create','/api/system/user/',1,NULL,2,'Add','新增'),(3,NULL,NULL,NULL,'2026-08-27 18:04:38.959433','2026-08-27 18:04:38.959443','编辑','user:Update','/api/system/user/{id}/',2,NULL,2,'Edit','編輯'),(4,NULL,NULL,NULL,'2026-08-27 18:04:38.964095','2026-08-27 18:04:38.964115','删除','user:Delete','/api/system/user/{id}/',3,NULL,2,'Delete','刪除'),(5,NULL,NULL,NULL,'2026-08-27 18:04:38.968749','2026-08-27 18:04:38.968760','导出','user:Export','/api/system/user/export/',1,NULL,2,'Export','導出'),(6,NULL,NULL,NULL,'2026-08-27 18:04:38.973239','2026-08-27 18:04:38.973250','导入','user:Import','/api/system/user/import/',1,NULL,2,'Import','導入'),(7,NULL,NULL,NULL,'2026-08-27 18:04:38.977683','2026-08-27 18:04:38.977694','获取导入模板','user:ImportTemplate','/api/system/user/import/',0,NULL,2,'Get Import Template','獲取導入模板'),(8,NULL,NULL,NULL,'2026-08-27 18:04:38.982005','2026-08-27 18:04:38.982016','批量更新模板','user:BatchUpdateTemplate','/api/system/user/update_template/',0,NULL,2,'Batch Update Template','批量更新模板'),(9,NULL,NULL,NULL,'2026-08-27 18:04:38.986348','2026-08-27 18:04:38.986358','重设密码','user:ResetPassword','/api/system/user/{id}/reset_password/',2,NULL,2,'Reset Password','重設密碼'),(10,NULL,NULL,NULL,'2026-08-27 18:04:38.991902','2026-08-27 18:04:38.991915','重置密码','user:ResetDefaultPassword','/api/system/user/{id}/reset_to_default_password/',2,NULL,2,'Reset Password','重置密碼'),(11,NULL,NULL,NULL,'2026-08-27 18:04:39.063443','2026-08-27 18:04:39.063454','查询','menu:Search','/api/system/menu/',0,NULL,3,'Search','查詢'),(12,NULL,NULL,NULL,'2026-08-27 18:04:39.068606','2026-08-27 18:04:39.068616','单例','menu:Retrieve','/api/system/menu/{id}/',0,NULL,3,'Retrieve','單例'),(13,NULL,NULL,NULL,'2026-08-27 18:04:39.072755','2026-08-27 18:04:39.072766','新增','menu:Create','/api/system/menu/',1,NULL,3,'Add','新增'),(14,NULL,NULL,NULL,'2026-08-27 18:04:39.077089','2026-08-27 18:04:39.077101','编辑','menu:Update','/api/system/menu/{id}/',2,NULL,3,'Edit','編輯'),(15,NULL,NULL,NULL,'2026-08-27 18:04:39.081732','2026-08-27 18:04:39.081743','删除','menu:Delete','/api/system/menu/{id}/',3,NULL,3,'Delete','刪除'),(16,NULL,NULL,NULL,'2026-08-27 18:04:39.086364','2026-08-27 18:04:39.086374','查询所有','menu:SearchAll','/api/system/menu/get_all_menu/',0,NULL,3,'Query All','查詢所有'),(17,NULL,NULL,NULL,'2026-08-27 18:04:39.090852','2026-08-27 18:04:39.090863','路由','menu:router','/api/system/menu/web_router/',0,NULL,3,'Route','路由'),(18,NULL,NULL,NULL,'2026-08-27 18:04:39.095025','2026-08-27 18:04:39.095036','查询按钮','menu:SearchButton','/api/system/menu_button/',0,NULL,3,'Query Buttons','查詢按鈕'),(19,NULL,NULL,NULL,'2026-08-27 18:04:39.099456','2026-08-27 18:04:39.099492','新增按钮','menu:CreateButton','/api/system/menu_button/',1,NULL,3,'Add Button','新增按鈕'),(20,NULL,NULL,NULL,'2026-08-27 18:04:39.103918','2026-08-27 18:04:39.103930','编辑按钮','menu:UpdateButton','/api/system/menu_button/{id}/',2,NULL,3,'Edit Button','編輯按鈕'),(21,NULL,NULL,NULL,'2026-08-27 18:04:39.108396','2026-08-27 18:04:39.108408','删除按钮','menu:DeleteButton','/api/system/menu_button/{id}/',3,NULL,3,'Delete Button','刪除按鈕'),(22,NULL,NULL,NULL,'2026-08-27 18:04:39.112933','2026-08-27 18:04:39.112945','上移','menu:MoveUp','/api/system/menu/mode_up/',1,NULL,3,'Move Up','上移'),(23,NULL,NULL,NULL,'2026-08-27 18:04:39.117673','2026-08-27 18:04:39.117682','下移','menu:MoveDown','/api/system/menu/mode_down/',1,NULL,3,'Move Down','下移'),(24,NULL,NULL,NULL,'2026-08-27 18:04:39.122123','2026-08-27 18:04:39.122136','查询列权限','column:Search','/api/system/column/',0,NULL,3,'Query Column Perms','查詢列權限'),(25,NULL,NULL,NULL,'2026-08-27 18:04:39.126620','2026-08-27 18:04:39.126632','新增列权限','column:Create','/api/system/column/',1,NULL,3,'Add Column Perms','新增列權限'),(26,NULL,NULL,NULL,'2026-08-27 18:04:39.130963','2026-08-27 18:04:39.130974','编辑列权限','column:Update','/api/system/column/{id}/',2,NULL,3,'Edit Column Perms','編輯列權限'),(27,NULL,NULL,NULL,'2026-08-27 18:04:39.137021','2026-08-27 18:04:39.137034','删除列权限','column:Delete','/api/system/column/{id}/',3,NULL,3,'Delete Column Perms','刪除列權限'),(28,NULL,NULL,NULL,'2026-08-27 18:04:39.142517','2026-08-27 18:04:39.142528','自动匹配列权限','column:Match','/api/system/column/auto_match_fields/',1,NULL,3,'Auto Match Col Perms','自動匹配列權限'),(29,NULL,NULL,NULL,'2026-08-27 18:04:39.151494','2026-08-27 18:04:39.151504','查询','dept:Search','/api/system/dept/',0,NULL,4,'Search','查詢'),(30,NULL,NULL,NULL,'2026-08-27 18:04:39.156229','2026-08-27 18:04:39.156241','详情','dept:Retrieve','/api/system/dept/{id}/',0,NULL,4,'Detail','詳情'),(31,NULL,NULL,NULL,'2026-08-27 18:04:39.160662','2026-08-27 18:04:39.160673','获取所有部门','dept:SearchAll','/api/system/dept/all_dept/',0,NULL,4,'Get All Depts','獲取所有部門'),(32,NULL,NULL,NULL,'2026-08-27 18:04:39.164912','2026-08-27 18:04:39.164922','部门顶部信息','dept:HeaderInfo','/api/system/dept/dept_info/',0,NULL,4,'Dept Header Info','部門頂部資訊'),(33,NULL,NULL,NULL,'2026-08-27 18:04:39.169559','2026-08-27 18:04:39.169570','新增','dept:Create','/api/system/dept/',1,NULL,4,'Add','新增'),(34,NULL,NULL,NULL,'2026-08-27 18:04:39.173978','2026-08-27 18:04:39.173989','上移','dept:MoveUp','/api/system/dept/mode_up/',1,NULL,4,'Move Up','上移'),(35,NULL,NULL,NULL,'2026-08-27 18:04:39.178805','2026-08-27 18:04:39.178815','下移','dept:MoveDown','/api/system/dept/mode_down/',1,NULL,4,'Move Down','下移'),(36,NULL,NULL,NULL,'2026-08-27 18:04:39.183241','2026-08-27 18:04:39.183254','编辑','dept:Update','/api/system/dept/{id}/',2,NULL,4,'Edit','編輯'),(37,NULL,NULL,NULL,'2026-08-27 18:04:39.187674','2026-08-27 18:04:39.187686','删除','dept:Delete','/api/system/dept/{id}/',3,NULL,4,'Delete','刪除'),(38,NULL,NULL,NULL,'2026-08-27 18:04:39.197157','2026-08-27 18:04:39.197168','查询','role:Search','/api/system/role/',0,NULL,5,'Search','查詢'),(39,NULL,NULL,NULL,'2026-08-27 18:04:39.201530','2026-08-27 18:04:39.201540','单例','role:Retrieve','/api/system/role/{id}/',0,NULL,5,'Retrieve','單例'),(40,NULL,NULL,NULL,'2026-08-27 18:04:39.206831','2026-08-27 18:04:39.206842','新增','role:Create','/api/system/role/',1,NULL,5,'Add','新增'),(41,NULL,NULL,NULL,'2026-08-27 18:04:39.211265','2026-08-27 18:04:39.211276','编辑','role:Update','/api/system/role/{id}/',2,NULL,5,'Edit','編輯'),(42,NULL,NULL,NULL,'2026-08-27 18:04:39.215818','2026-08-27 18:04:39.215830','删除','role:Delete','/api/system/role/{id}/',3,NULL,5,'Delete','刪除'),(43,NULL,NULL,NULL,'2026-08-27 18:04:39.220385','2026-08-27 18:04:39.220396','获取所有可授权数据范围的部门','role:AllDataRangeDept','/api/system/role_menu_button_permision/role_to_dept_all/',0,NULL,5,'Get Assignable Depts','獲取所有可授權數據範圍的部門'),(44,NULL,NULL,NULL,'2026-08-27 18:04:39.224784','2026-08-27 18:04:39.224796','获取所有可授权菜单','role:AllCanMenu','/api/system/role_menu_button_permision/get_role_menu/',0,NULL,5,'Get All Assignable Menus','獲取所有可授權選單'),(45,NULL,NULL,NULL,'2026-08-27 18:04:39.229160','2026-08-27 18:04:39.229171','获取所有已授权用户','role:AllAuthorizedUser','/api/system/role/get_role_users/',0,NULL,5,'Get Authorized Users','獲取所有已授權用戶'),(46,NULL,NULL,NULL,'2026-08-27 18:04:39.233564','2026-08-27 18:04:39.233575','获取菜单所有可授权按钮','role:AllMenuButton','/api/system/role_menu_button_permision/get_role_menu_btn_field/',0,NULL,5,'Get All Assignable Buttons','獲取選單所有可授權按鈕'),(47,NULL,NULL,NULL,'2026-08-27 18:04:39.238061','2026-08-27 18:04:39.238072','授权菜单','role:SetMenu','/api/system/role_menu_button_permision/set_role_menu/',2,NULL,5,'Assign Menu','授權選單'),(48,NULL,NULL,NULL,'2026-08-27 18:04:39.242429','2026-08-27 18:04:39.242440','授权菜单按钮','role:SetMenuButton','/api/system/role_menu_button_permision/set_role_menu_btn/',2,NULL,5,'Assign Menu Buttons','授權選單按鈕'),(49,NULL,NULL,NULL,'2026-08-27 18:04:39.246719','2026-08-27 18:04:39.246731','授权数据范围','role:SetDataRange','/api/system/role_menu_button_permision/set_role_menu_btn_data_range/',2,NULL,5,'Assign Data Range','授權數據範圍'),(50,NULL,NULL,NULL,'2026-08-27 18:04:39.250879','2026-08-27 18:04:39.250890','获取所有用户','role:AllUser','/api/system/user/',0,NULL,5,'Get All Users','獲取所有用戶'),(51,NULL,NULL,NULL,'2026-08-27 18:04:39.255059','2026-08-27 18:04:39.255070','授权用户予角色','role:SetUserRole','/api/system/role/{id}/set_role_users/',2,NULL,5,'Assign Users to Role','授權用戶予角色'),(52,NULL,NULL,NULL,'2026-08-27 18:04:39.309026','2026-08-27 18:04:39.309037','查询','messageCenter:Search','/api/system/message_center/',0,NULL,6,'Search','查詢'),(53,NULL,NULL,NULL,'2026-08-27 18:04:39.312958','2026-08-27 18:04:39.312968','详情','messageCenter:Retrieve','/api/system/message_center/{id}/',0,NULL,6,'Detail','詳情'),(54,NULL,NULL,NULL,'2026-08-27 18:04:39.317384','2026-08-27 18:04:39.317394','新增','messageCenter:Create','/api/system/message_center/',1,NULL,6,'Add','新增'),(55,NULL,NULL,NULL,'2026-08-27 18:04:39.321648','2026-08-27 18:04:39.321658','编辑','messageCenter:Update','/api/system/message_center/{id}/',2,NULL,6,'Edit','編輯'),(56,NULL,NULL,NULL,'2026-08-27 18:04:39.325924','2026-08-27 18:04:39.325936','删除','messageCenter:Delete','/api/system/menu/{id}/',3,NULL,6,'Delete','刪除'),(57,NULL,NULL,NULL,'2026-08-27 18:04:39.375768','2026-08-27 18:04:39.375778','查询','api_white_list:Search','/api/system/api_white_list/',0,NULL,7,'Search','查詢'),(58,NULL,NULL,NULL,'2026-08-27 18:04:39.380093','2026-08-27 18:04:39.380105','详情','api_white_list:Retrieve','/api/system/api_white_list/{id}/',0,NULL,7,'Detail','詳情'),(59,NULL,NULL,NULL,'2026-08-27 18:04:39.384273','2026-08-27 18:04:39.384283','新增','api_white_list:Create','/api/system/api_white_list/',1,NULL,7,'Add','新增'),(60,NULL,NULL,NULL,'2026-08-27 18:04:39.388940','2026-08-27 18:04:39.388951','编辑','api_white_list:Update','/api/system/api_white_list/{id}/',2,NULL,7,'Edit','編輯'),(61,NULL,NULL,NULL,'2026-08-27 18:04:39.393259','2026-08-27 18:04:39.393269','删除','api_white_list:Delete','/api/system/api_white_list/{id}/',3,NULL,7,'Delete','刪除'),(62,NULL,NULL,NULL,'2026-08-27 18:04:39.445022','2026-08-27 18:04:39.445033','查询','downloadCenter:Search','/api/system/download_center/',0,NULL,8,'Search','查詢'),(63,NULL,NULL,NULL,'2026-08-27 18:04:39.458781','2026-08-27 18:04:39.458791','查询','system_config:Search','/api/system/system_config/',0,NULL,10,'Search','查詢'),(64,NULL,NULL,NULL,'2026-08-27 18:04:39.463033','2026-08-27 18:04:39.463046','详情','system_config:Retrieve','/api/system/system_config/{id}/',0,NULL,10,'Detail','詳情'),(65,NULL,NULL,NULL,'2026-08-27 18:04:39.467337','2026-08-27 18:04:39.467348','新增','system_config:Create','/api/system/system_config/',1,NULL,10,'Add','新增'),(66,NULL,NULL,NULL,'2026-08-27 18:04:39.472128','2026-08-27 18:04:39.472138','编辑','system_config:Update','/api/system/system_config/{id}/',2,NULL,10,'Edit','編輯'),(67,NULL,NULL,NULL,'2026-08-27 18:04:39.476746','2026-08-27 18:04:39.476759','删除','system_config:Delete','/api/system/system_config/{id}/',3,NULL,10,'Delete','刪除'),(68,NULL,NULL,NULL,'2026-08-27 18:04:39.486594','2026-08-27 18:04:39.486604','查询','dictionary:Search','/api/system/dictionary/',0,NULL,11,'Search','查詢'),(69,NULL,NULL,NULL,'2026-08-27 18:04:39.490847','2026-08-27 18:04:39.490858','详情','dictionary:Retrieve','/api/system/dictionary/{id}/',0,NULL,11,'Detail','詳情'),(70,NULL,NULL,NULL,'2026-08-27 18:04:39.495070','2026-08-27 18:04:39.495080','新增','dictionary:Create','/api/system/dictionary/',1,NULL,11,'Add','新增'),(71,NULL,NULL,NULL,'2026-08-27 18:04:39.499699','2026-08-27 18:04:39.499709','编辑','dictionary:Update','/api/system/dictionary/{id}/',2,NULL,11,'Edit','編輯'),(72,NULL,NULL,NULL,'2026-08-27 18:04:39.505632','2026-08-27 18:04:39.505644','删除','dictionary:Delete','/api/system/dictionary/{id}/',3,NULL,11,'Delete','刪除'),(73,NULL,NULL,NULL,'2026-08-27 18:04:39.581684','2026-08-27 18:04:39.581695','查询','area:Search','/api/system/area/',0,NULL,12,'Search','查詢'),(74,NULL,NULL,NULL,'2026-08-27 18:04:39.586382','2026-08-27 18:04:39.586394','详情','area:Retrieve','/api/system/area/{id}/',0,NULL,12,'Detail','詳情'),(75,NULL,NULL,NULL,'2026-08-27 18:04:39.590964','2026-08-27 18:04:39.590974','新增','area:Create','/api/system/area/',1,NULL,12,'Add','新增'),(76,NULL,NULL,NULL,'2026-08-27 18:04:39.595383','2026-08-27 18:04:39.595394','编辑','area:Update','/api/system/area/{id}/',2,NULL,12,'Edit','編輯'),(77,NULL,NULL,NULL,'2026-08-27 18:04:39.600514','2026-08-27 18:04:39.600526','删除','area:Delete','/api/system/area/{id}/',3,NULL,12,'Delete','刪除'),(78,NULL,NULL,NULL,'2026-08-27 18:04:39.669077','2026-08-27 18:04:39.669088','详情','file:Retrieve','/api/system/file/{id}/',0,NULL,13,'Detail','詳情'),(79,NULL,NULL,NULL,'2026-08-27 18:04:39.675281','2026-08-27 18:04:39.675293','查询','file:Search','/api/system/file/',0,NULL,13,'Search','查詢'),(80,NULL,NULL,NULL,'2026-08-27 18:04:39.679723','2026-08-27 18:04:39.679735','编辑','file:Update','/api/system/file/{id}/',1,NULL,13,'Edit','編輯'),(81,NULL,NULL,NULL,'2026-08-27 18:04:39.684088','2026-08-27 18:04:39.684099','删除','file:Delete','/api/system/file/{id}/',3,NULL,13,'Delete','刪除'),(82,NULL,NULL,NULL,'2026-08-27 18:04:39.758937','2026-08-27 18:04:39.758948','查询','login_log:Search','/api/system/login_log/',0,NULL,15,'Search','查詢'),(83,NULL,NULL,NULL,'2026-08-27 18:04:39.763994','2026-08-27 18:04:39.764005','详情','login_log:Retrieve','/api/system/login_log/{id}/',0,NULL,15,'Detail','詳情'),(84,NULL,NULL,NULL,'2026-08-27 18:04:39.874874','2026-08-27 18:04:39.874884','详情','operation_log:Retrieve','/api/system/operation_log/{id}/',0,NULL,16,'Detail','詳情'),(85,NULL,NULL,NULL,'2026-08-27 18:04:39.879268','2026-08-27 18:04:39.879278','查询','operation_log:Search','/api/system/operation_log/',0,NULL,16,'Search','查詢'),(86,NULL,NULL,NULL,'2026-08-28 15:07:13.930656','2026-08-28 15:07:13.930667','复制','menu:Copy','/api/menu/',1,NULL,3,'Copy','複製'),(87,NULL,NULL,NULL,'2026-08-28 15:07:13.930685','2026-08-28 15:07:13.930689','导入','menu:Import','/api/menu/import_data/',1,NULL,3,'Import','導入'),(88,NULL,NULL,NULL,'2026-08-28 15:07:13.930701','2026-08-28 15:07:13.930705','导出','menu:Export','/api/menu/export_data/',1,NULL,3,'Export','導出'),(89,NULL,NULL,NULL,'2026-08-31 13:50:46.192659','2026-08-31 13:50:46.192683','查看','dispatch:View','/api/bastion/dispatch/{id}/',0,NULL,38,NULL,NULL),(90,NULL,NULL,NULL,'2026-08-31 13:50:46.196727','2026-08-31 13:50:46.196737','执行','dispatch:Execute','/api/bastion/dispatch/{id}/execute/',1,NULL,38,NULL,NULL),(91,NULL,NULL,NULL,'2026-08-31 13:50:46.199803','2026-08-31 13:50:46.199813','重试失败','dispatch:Retry','/api/bastion/dispatch/{id}/execute/',1,NULL,38,NULL,NULL),(92,NULL,NULL,NULL,'2026-08-31 13:50:46.202897','2026-08-31 13:50:46.202921','删除','dispatch:Delete','/api/bastion/dispatch/{id}/',3,NULL,38,NULL,NULL);
/*!40000 ALTER TABLE `dvadmin_system_menu_button` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_menu_field`
--

DROP TABLE IF EXISTS `dvadmin_system_menu_field`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_menu_field` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `model` varchar(64) NOT NULL,
  `field_name` varchar(64) NOT NULL,
  `title` varchar(64) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  `menu_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_menu_field_creator_id_084838f6` (`creator_id`),
  KEY `dvadmin_system_menu_field_menu_id_ebf37091` (`menu_id`)
) ENGINE=InnoDB AUTO_INCREMENT=133 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_menu_field`
--

LOCK TABLES `dvadmin_system_menu_field` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_menu_field` DISABLE KEYS */;
INSERT INTO `dvadmin_system_menu_field` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:38.996283','2026-08-27 18:04:38.996293','Users','avatar','头像',NULL,2),(2,NULL,NULL,NULL,'2026-08-27 18:04:39.000216','2026-08-27 18:04:39.000226','Users','create_datetime','创建时间',NULL,2),(3,NULL,NULL,NULL,'2026-08-27 18:04:39.004428','2026-08-27 18:04:39.004439','Users','creator','创建人',NULL,2),(4,NULL,NULL,NULL,'2026-08-27 18:04:39.009625','2026-08-27 18:04:39.009636','Users','dept','所属部门',NULL,2),(5,NULL,NULL,NULL,'2026-08-27 18:04:39.013673','2026-08-27 18:04:39.013683','Users','dept_belong_id','数据归属部门',NULL,2),(6,NULL,NULL,NULL,'2026-08-27 18:04:39.017673','2026-08-27 18:04:39.017684','Users','description','描述',NULL,2),(7,NULL,NULL,NULL,'2026-08-27 18:04:39.021895','2026-08-27 18:04:39.021906','Users','email','邮箱',NULL,2),(8,NULL,NULL,NULL,'2026-08-27 18:04:39.026115','2026-08-27 18:04:39.026126','Users','gender','性别',NULL,2),(9,NULL,NULL,NULL,'2026-08-27 18:04:39.030120','2026-08-27 18:04:39.030131','Users','id','Id',NULL,2),(10,NULL,NULL,NULL,'2026-08-27 18:04:39.034815','2026-08-27 18:04:39.034825','Users','mobile','电话',NULL,2),(11,NULL,NULL,NULL,'2026-08-27 18:04:39.039069','2026-08-27 18:04:39.039079','Users','modifier','修改人',NULL,2),(12,NULL,NULL,NULL,'2026-08-27 18:04:39.043085','2026-08-27 18:04:39.043095','Users','name','姓名',NULL,2),(13,NULL,NULL,NULL,'2026-08-27 18:04:39.046926','2026-08-27 18:04:39.046937','Users','update_datetime','修改时间',NULL,2),(14,NULL,NULL,NULL,'2026-08-27 18:04:39.050760','2026-08-27 18:04:39.050770','Users','username','用户账号',NULL,2),(15,NULL,NULL,NULL,'2026-08-27 18:04:39.054415','2026-08-27 18:04:39.054426','Users','user_type','用户类型',NULL,2),(16,NULL,NULL,NULL,'2026-08-27 18:04:39.258856','2026-08-27 18:04:39.258866','Role','create_datetime','创建时间',NULL,5),(17,NULL,NULL,NULL,'2026-08-27 18:04:39.262501','2026-08-27 18:04:39.262511','Role','creator','创建人',NULL,5),(18,NULL,NULL,NULL,'2026-08-27 18:04:39.267175','2026-08-27 18:04:39.267186','Role','dept_belong_id','数据归属部门',NULL,5),(19,NULL,NULL,NULL,'2026-08-27 18:04:39.271226','2026-08-27 18:04:39.271236','Role','description','描述',NULL,5),(20,NULL,NULL,NULL,'2026-08-27 18:04:39.275041','2026-08-27 18:04:39.275051','Role','id','Id',NULL,5),(21,NULL,NULL,NULL,'2026-08-27 18:04:39.279098','2026-08-27 18:04:39.279115','Role','key','权限字符',NULL,5),(22,NULL,NULL,NULL,'2026-08-27 18:04:39.282934','2026-08-27 18:04:39.282944','Role','modifier','修改人',NULL,5),(23,NULL,NULL,NULL,'2026-08-27 18:04:39.286649','2026-08-27 18:04:39.286658','Role','name','角色名称',NULL,5),(24,NULL,NULL,NULL,'2026-08-27 18:04:39.290347','2026-08-27 18:04:39.290357','Role','sort','角色顺序',NULL,5),(25,NULL,NULL,NULL,'2026-08-27 18:04:39.294182','2026-08-27 18:04:39.294191','Role','status','角色状态',NULL,5),(26,NULL,NULL,NULL,'2026-08-27 18:04:39.298603','2026-08-27 18:04:39.298613','Role','update_datetime','修改时间',NULL,5),(27,NULL,NULL,NULL,'2026-08-27 18:04:39.329970','2026-08-27 18:04:39.329981','MessageCenter','content','内容',NULL,6),(28,NULL,NULL,NULL,'2026-08-27 18:04:39.334013','2026-08-27 18:04:39.334026','MessageCenter','create_datetime','创建时间',NULL,6),(29,NULL,NULL,NULL,'2026-08-27 18:04:39.338784','2026-08-27 18:04:39.338795','MessageCenter','creator','创建人',NULL,6),(30,NULL,NULL,NULL,'2026-08-27 18:04:39.342612','2026-08-27 18:04:39.342623','MessageCenter','dept_belong_id','数据归属部门',NULL,6),(31,NULL,NULL,NULL,'2026-08-27 18:04:39.346410','2026-08-27 18:04:39.346422','MessageCenter','description','描述',NULL,6),(32,NULL,NULL,NULL,'2026-08-27 18:04:39.350355','2026-08-27 18:04:39.350365','MessageCenter','id','Id',NULL,6),(33,NULL,NULL,NULL,'2026-08-27 18:04:39.354332','2026-08-27 18:04:39.354343','MessageCenter','modifier','修改人',NULL,6),(34,NULL,NULL,NULL,'2026-08-27 18:04:39.358295','2026-08-27 18:04:39.358305','MessageCenter','target_type','目标类型',NULL,6),(35,NULL,NULL,NULL,'2026-08-27 18:04:39.362544','2026-08-27 18:04:39.362554','MessageCenter','title','标题',NULL,6),(36,NULL,NULL,NULL,'2026-08-27 18:04:39.366286','2026-08-27 18:04:39.366296','MessageCenter','update_datetime','修改时间',NULL,6),(37,NULL,NULL,NULL,'2026-08-27 18:04:39.397357','2026-08-27 18:04:39.397367','ApiWhiteList','create_datetime','创建时间',NULL,7),(38,NULL,NULL,NULL,'2026-08-27 18:04:39.402423','2026-08-27 18:04:39.402433','ApiWhiteList','creator','创建人',NULL,7),(39,NULL,NULL,NULL,'2026-08-27 18:04:39.406208','2026-08-27 18:04:39.406218','ApiWhiteList','dept_belong_id','数据归属部门',NULL,7),(40,NULL,NULL,NULL,'2026-08-27 18:04:39.410981','2026-08-27 18:04:39.410992','ApiWhiteList','description','描述',NULL,7),(41,NULL,NULL,NULL,'2026-08-27 18:04:39.414718','2026-08-27 18:04:39.414728','ApiWhiteList','enable_datasource','激活数据权限',NULL,7),(42,NULL,NULL,NULL,'2026-08-27 18:04:39.418588','2026-08-27 18:04:39.418598','ApiWhiteList','id','Id',NULL,7),(43,NULL,NULL,NULL,'2026-08-27 18:04:39.422421','2026-08-27 18:04:39.422431','ApiWhiteList','method','接口请求方法',NULL,7),(44,NULL,NULL,NULL,'2026-08-27 18:04:39.426541','2026-08-27 18:04:39.426552','ApiWhiteList','modifier','修改人',NULL,7),(45,NULL,NULL,NULL,'2026-08-27 18:04:39.430790','2026-08-27 18:04:39.430800','ApiWhiteList','update_datetime','修改时间',NULL,7),(46,NULL,NULL,NULL,'2026-08-27 18:04:39.435902','2026-08-27 18:04:39.435913','ApiWhiteList','url','url',NULL,7),(47,NULL,NULL,NULL,'2026-08-27 18:04:39.510049','2026-08-27 18:04:39.510060','Dictionary','color','颜色',NULL,11),(48,NULL,NULL,NULL,'2026-08-27 18:04:39.513916','2026-08-27 18:04:39.513925','Dictionary','create_datetime','创建时间',NULL,11),(49,NULL,NULL,NULL,'2026-08-27 18:04:39.517728','2026-08-27 18:04:39.517739','Dictionary','creator','创建人',NULL,11),(50,NULL,NULL,NULL,'2026-08-27 18:04:39.521746','2026-08-27 18:04:39.521757','Dictionary','dept_belong_id','数据归属部门',NULL,11),(51,NULL,NULL,NULL,'2026-08-27 18:04:39.525714','2026-08-27 18:04:39.525725','Dictionary','description','描述',NULL,11),(52,NULL,NULL,NULL,'2026-08-27 18:04:39.529754','2026-08-27 18:04:39.529765','Dictionary','id','Id',NULL,11),(53,NULL,NULL,NULL,'2026-08-27 18:04:39.533753','2026-08-27 18:04:39.533763','Dictionary','is_value','是否为value值',NULL,11),(54,NULL,NULL,NULL,'2026-08-27 18:04:39.537651','2026-08-27 18:04:39.537661','Dictionary','label','字典名称',NULL,11),(55,NULL,NULL,NULL,'2026-08-27 18:04:39.541458','2026-08-27 18:04:39.541468','Dictionary','modifier','修改人',NULL,11),(56,NULL,NULL,NULL,'2026-08-27 18:04:39.545638','2026-08-27 18:04:39.545649','Dictionary','parent','父级',NULL,11),(57,NULL,NULL,NULL,'2026-08-27 18:04:39.549610','2026-08-27 18:04:39.549620','Dictionary','remark','备注',NULL,11),(58,NULL,NULL,NULL,'2026-08-27 18:04:39.554828','2026-08-27 18:04:39.554838','Dictionary','sort','显示排序',NULL,11),(59,NULL,NULL,NULL,'2026-08-27 18:04:39.558977','2026-08-27 18:04:39.558987','Dictionary','status','状态',NULL,11),(60,NULL,NULL,NULL,'2026-08-27 18:04:39.562940','2026-08-27 18:04:39.562950','Dictionary','type','数据值类型',NULL,11),(61,NULL,NULL,NULL,'2026-08-27 18:04:39.567331','2026-08-27 18:04:39.567342','Dictionary','update_datetime','修改时间',NULL,11),(62,NULL,NULL,NULL,'2026-08-27 18:04:39.572258','2026-08-27 18:04:39.572268','Dictionary','value','字典编号',NULL,11),(63,NULL,NULL,NULL,'2026-08-27 18:04:39.605454','2026-08-27 18:04:39.605464','Area','code','地区编码',NULL,12),(64,NULL,NULL,NULL,'2026-08-27 18:04:39.609397','2026-08-27 18:04:39.609409','Area','create_datetime','创建时间',NULL,12),(65,NULL,NULL,NULL,'2026-08-27 18:04:39.613406','2026-08-27 18:04:39.613417','Area','creator','创建人',NULL,12),(66,NULL,NULL,NULL,'2026-08-27 18:04:39.617396','2026-08-27 18:04:39.617406','Area','dept_belong_id','数据归属部门',NULL,12),(67,NULL,NULL,NULL,'2026-08-27 18:04:39.621588','2026-08-27 18:04:39.621599','Area','description','描述',NULL,12),(68,NULL,NULL,NULL,'2026-08-27 18:04:39.626180','2026-08-27 18:04:39.626193','Area','enable','是否启用',NULL,12),(69,NULL,NULL,NULL,'2026-08-27 18:04:39.630993','2026-08-27 18:04:39.631005','Area','id','Id',NULL,12),(70,NULL,NULL,NULL,'2026-08-27 18:04:39.635194','2026-08-27 18:04:39.635205','Area','initials','首字母',NULL,12),(71,NULL,NULL,NULL,'2026-08-27 18:04:39.639363','2026-08-27 18:04:39.639375','Area','level','地区层级(1省份 2城市 3区县 4乡级)',NULL,12),(72,NULL,NULL,NULL,'2026-08-27 18:04:39.643736','2026-08-27 18:04:39.643747','Area','modifier','修改人',NULL,12),(73,NULL,NULL,NULL,'2026-08-27 18:04:39.647692','2026-08-27 18:04:39.647702','Area','name','名称',NULL,12),(74,NULL,NULL,NULL,'2026-08-27 18:04:39.651836','2026-08-27 18:04:39.651846','Area','pcode','父地区编码',NULL,12),(75,NULL,NULL,NULL,'2026-08-27 18:04:39.655887','2026-08-27 18:04:39.655897','Area','pinyin','拼音',NULL,12),(76,NULL,NULL,NULL,'2026-08-27 18:04:39.659987','2026-08-27 18:04:39.659999','Area','update_datetime','修改时间',NULL,12),(77,NULL,NULL,NULL,'2026-08-27 18:04:39.688062','2026-08-27 18:04:39.688073','FileList','create_datetime','创建时间',NULL,13),(78,NULL,NULL,NULL,'2026-08-27 18:04:39.693293','2026-08-27 18:04:39.693304','FileList','creator','创建人',NULL,13),(79,NULL,NULL,NULL,'2026-08-27 18:04:39.697104','2026-08-27 18:04:39.697114','FileList','dept_belong_id','数据归属部门',NULL,13),(80,NULL,NULL,NULL,'2026-08-27 18:04:39.701166','2026-08-27 18:04:39.701176','FileList','description','描述',NULL,13),(81,NULL,NULL,NULL,'2026-08-27 18:04:39.706001','2026-08-27 18:04:39.706011','FileList','engine','引擎',NULL,13),(82,NULL,NULL,NULL,'2026-08-27 18:04:39.710022','2026-08-27 18:04:39.710033','FileList','file_url','文件地址',NULL,13),(83,NULL,NULL,NULL,'2026-08-27 18:04:39.714279','2026-08-27 18:04:39.714289','FileList','id','Id',NULL,13),(84,NULL,NULL,NULL,'2026-08-27 18:04:39.718255','2026-08-27 18:04:39.718265','FileList','md5sum','文件md5',NULL,13),(85,NULL,NULL,NULL,'2026-08-27 18:04:39.723810','2026-08-27 18:04:39.723820','FileList','mime_type','Mime类型',NULL,13),(86,NULL,NULL,NULL,'2026-08-27 18:04:39.728046','2026-08-27 18:04:39.728057','FileList','modifier','修改人',NULL,13),(87,NULL,NULL,NULL,'2026-08-27 18:04:39.731843','2026-08-27 18:04:39.731854','FileList','name','名称',NULL,13),(88,NULL,NULL,NULL,'2026-08-27 18:04:39.736070','2026-08-27 18:04:39.736081','FileList','size','文件大小',NULL,13),(89,NULL,NULL,NULL,'2026-08-27 18:04:39.740067','2026-08-27 18:04:39.740077','FileList','update_datetime','修改时间',NULL,13),(90,NULL,NULL,NULL,'2026-08-27 18:04:39.744169','2026-08-27 18:04:39.744181','FileList','url','url',NULL,13),(91,NULL,NULL,NULL,'2026-08-27 18:04:39.768829','2026-08-27 18:04:39.768839','LoginLog','agent','agent信息',NULL,15),(92,NULL,NULL,NULL,'2026-08-27 18:04:39.772870','2026-08-27 18:04:39.772881','LoginLog','area_code','区域代码',NULL,15),(93,NULL,NULL,NULL,'2026-08-27 18:04:39.777029','2026-08-27 18:04:39.777040','LoginLog','browser','浏览器名',NULL,15),(94,NULL,NULL,NULL,'2026-08-27 18:04:39.781147','2026-08-27 18:04:39.781158','LoginLog','city','城市',NULL,15),(95,NULL,NULL,NULL,'2026-08-27 18:04:39.785930','2026-08-27 18:04:39.785941','LoginLog','continent','州',NULL,15),(96,NULL,NULL,NULL,'2026-08-27 18:04:39.789919','2026-08-27 18:04:39.789929','LoginLog','country','国家',NULL,15),(97,NULL,NULL,NULL,'2026-08-27 18:04:39.793995','2026-08-27 18:04:39.794006','LoginLog','country_code','简称',NULL,15),(98,NULL,NULL,NULL,'2026-08-27 18:04:39.798763','2026-08-27 18:04:39.798772','LoginLog','country_english','英文全称',NULL,15),(99,NULL,NULL,NULL,'2026-08-27 18:04:39.802685','2026-08-27 18:04:39.802695','LoginLog','create_datetime','创建时间',NULL,15),(100,NULL,NULL,NULL,'2026-08-27 18:04:39.806538','2026-08-27 18:04:39.806548','LoginLog','creator','创建人',NULL,15),(101,NULL,NULL,NULL,'2026-08-27 18:04:39.811013','2026-08-27 18:04:39.811024','LoginLog','dept_belong_id','数据归属部门',NULL,15),(102,NULL,NULL,NULL,'2026-08-27 18:04:39.815091','2026-08-27 18:04:39.815101','LoginLog','description','描述',NULL,15),(103,NULL,NULL,NULL,'2026-08-27 18:04:39.819301','2026-08-27 18:04:39.819311','LoginLog','district','县区',NULL,15),(104,NULL,NULL,NULL,'2026-08-27 18:04:39.824271','2026-08-27 18:04:39.824282','LoginLog','id','Id',NULL,15),(105,NULL,NULL,NULL,'2026-08-27 18:04:39.828199','2026-08-27 18:04:39.828211','LoginLog','ip','登录ip',NULL,15),(106,NULL,NULL,NULL,'2026-08-27 18:04:39.832270','2026-08-27 18:04:39.832281','LoginLog','isp','运营商',NULL,15),(107,NULL,NULL,NULL,'2026-08-27 18:04:39.836160','2026-08-27 18:04:39.836171','LoginLog','latitude','纬度',NULL,15),(108,NULL,NULL,NULL,'2026-08-27 18:04:39.840973','2026-08-27 18:04:39.840983','LoginLog','login_type','登录类型',NULL,15),(109,NULL,NULL,NULL,'2026-08-27 18:04:39.845217','2026-08-27 18:04:39.845228','LoginLog','longitude','经度',NULL,15),(110,NULL,NULL,NULL,'2026-08-27 18:04:39.849545','2026-08-27 18:04:39.849555','LoginLog','modifier','修改人',NULL,15),(111,NULL,NULL,NULL,'2026-08-27 18:04:39.853679','2026-08-27 18:04:39.853689','LoginLog','os','操作系统',NULL,15),(112,NULL,NULL,NULL,'2026-08-27 18:04:39.857546','2026-08-27 18:04:39.857558','LoginLog','province','省份',NULL,15),(113,NULL,NULL,NULL,'2026-08-27 18:04:39.862230','2026-08-27 18:04:39.862242','LoginLog','update_datetime','修改时间',NULL,15),(114,NULL,NULL,NULL,'2026-08-27 18:04:39.866030','2026-08-27 18:04:39.866040','LoginLog','username','登录用户名',NULL,15),(115,NULL,NULL,NULL,'2026-08-27 18:04:39.883415','2026-08-27 18:04:39.883426','OperationLog','create_datetime','创建时间',NULL,16),(116,NULL,NULL,NULL,'2026-08-27 18:04:39.887292','2026-08-27 18:04:39.887302','OperationLog','creator','创建人',NULL,16),(117,NULL,NULL,NULL,'2026-08-27 18:04:39.891099','2026-08-27 18:04:39.891109','OperationLog','dept_belong_id','数据归属部门',NULL,16),(118,NULL,NULL,NULL,'2026-08-27 18:04:39.894915','2026-08-27 18:04:39.894925','OperationLog','description','描述',NULL,16),(119,NULL,NULL,NULL,'2026-08-27 18:04:39.898744','2026-08-27 18:04:39.898754','OperationLog','id','Id',NULL,16),(120,NULL,NULL,NULL,'2026-08-27 18:04:39.902523','2026-08-27 18:04:39.902534','OperationLog','json_result','返回信息',NULL,16),(121,NULL,NULL,NULL,'2026-08-27 18:04:39.906586','2026-08-27 18:04:39.906597','OperationLog','modifier','修改人',NULL,16),(122,NULL,NULL,NULL,'2026-08-27 18:04:39.910608','2026-08-27 18:04:39.910618','OperationLog','request_body','请求参数',NULL,16),(123,NULL,NULL,NULL,'2026-08-27 18:04:39.914683','2026-08-27 18:04:39.914694','OperationLog','request_browser','请求浏览器',NULL,16),(124,NULL,NULL,NULL,'2026-08-27 18:04:39.918522','2026-08-27 18:04:39.918532','OperationLog','request_ip','请求ip地址',NULL,16),(125,NULL,NULL,NULL,'2026-08-27 18:04:39.922304','2026-08-27 18:04:39.922314','OperationLog','request_method','请求方式',NULL,16),(126,NULL,NULL,NULL,'2026-08-27 18:04:39.926409','2026-08-27 18:04:39.926419','OperationLog','request_modular','请求模块',NULL,16),(127,NULL,NULL,NULL,'2026-08-27 18:04:39.930532','2026-08-27 18:04:39.930544','OperationLog','request_msg','操作说明',NULL,16),(128,NULL,NULL,NULL,'2026-08-27 18:04:39.935324','2026-08-27 18:04:39.935334','OperationLog','request_os','操作系统',NULL,16),(129,NULL,NULL,NULL,'2026-08-27 18:04:39.939262','2026-08-27 18:04:39.939273','OperationLog','request_path','请求地址',NULL,16),(130,NULL,NULL,NULL,'2026-08-27 18:04:39.943088','2026-08-27 18:04:39.943099','OperationLog','response_code','响应状态码',NULL,16),(131,NULL,NULL,NULL,'2026-08-27 18:04:39.946930','2026-08-27 18:04:39.946954','OperationLog','status','响应状态',NULL,16),(132,NULL,NULL,NULL,'2026-08-27 18:04:39.950888','2026-08-27 18:04:39.950898','OperationLog','update_datetime','修改时间',NULL,16);
/*!40000 ALTER TABLE `dvadmin_system_menu_field` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_operation_log`
--

DROP TABLE IF EXISTS `dvadmin_system_operation_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_operation_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `request_modular` varchar(64) DEFAULT NULL,
  `request_path` varchar(400) DEFAULT NULL,
  `request_body` longtext,
  `request_method` varchar(8) DEFAULT NULL,
  `request_msg` longtext,
  `request_ip` varchar(32) DEFAULT NULL,
  `request_browser` varchar(64) DEFAULT NULL,
  `response_code` varchar(32) DEFAULT NULL,
  `request_os` varchar(64) DEFAULT NULL,
  `json_result` longtext,
  `status` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_operation_log_creator_id_0914479c` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=324 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_operation_log`
--

LOCK TABLES `dvadmin_system_operation_log` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_operation_log` DISABLE KEYS */;
INSERT INTO `dvadmin_system_operation_log` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:57.298347','2026-08-27 18:04:57.162076','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(2,NULL,NULL,'1','2026-08-27 18:11:54.786525','2026-08-27 18:11:54.274251','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'1\', \'captchaKey\': 2, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(3,NULL,NULL,'1','2026-08-27 18:12:15.336535','2026-08-27 18:12:15.240503','用户表','/api/system/user/login_change_password/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'password_regain\': \'6387f2e5cb4b4e307e087b34587def60\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(4,NULL,NULL,NULL,'2026-08-28 09:36:43.823029','2026-08-28 09:36:43.641203','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','401','Other','{\'code\': 401, \'msg\': ErrorDetail(string=\'账号/密码不正确\', code=\'no_active_account\')}',0,NULL),(5,NULL,NULL,NULL,'2026-08-28 09:36:59.193468','2026-08-28 09:36:59.013919','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','401','Other','{\'code\': 401, \'msg\': ErrorDetail(string=\'账号/密码不正确\', code=\'no_active_account\')}',0,NULL),(6,NULL,NULL,NULL,'2026-08-28 09:38:28.243817','2026-08-28 09:38:28.057072','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(7,NULL,NULL,NULL,'2026-08-28 09:39:04.698107','2026-08-28 09:39:04.511875','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(8,NULL,NULL,NULL,'2026-08-28 09:40:01.737294','2026-08-28 09:40:01.556416','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(9,NULL,NULL,NULL,'2026-08-28 09:40:35.664233','2026-08-28 09:40:35.471559','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(10,NULL,NULL,NULL,'2026-08-28 09:51:02.141370','2026-08-28 09:51:01.956192','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(11,NULL,NULL,NULL,'2026-08-28 09:57:28.315542','2026-08-28 09:57:28.121598','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'1\', \'captchaKey\': 4, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Username/password incorrect. Account will be locked after 4 failed attempts~\'}',0,NULL),(12,NULL,NULL,NULL,'2026-08-28 09:57:35.415914','2026-08-28 09:57:35.222885','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'14\', \'captchaKey\': 5, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Username/password incorrect. Account will be locked after 3 failed attempts~\'}',0,NULL),(13,NULL,NULL,'1','2026-08-28 09:57:58.478495','2026-08-28 09:57:58.146196','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'2\', \'captchaKey\': 6, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(14,NULL,NULL,'1','2026-08-28 09:58:52.931908','2026-08-28 09:58:52.920774','机房','/api/cmdb/idc/2/','{\'id\': 2}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(15,NULL,NULL,'1','2026-08-28 09:59:13.823365','2026-08-28 09:59:13.813056','机房','/api/cmdb/idc/','{\'sort\': 2, \'status\': 1, \'name\': \'2号机房\', \'code\': \'idc2\', \'location\': \'2号机房\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(16,NULL,NULL,NULL,'2026-08-28 10:14:21.010198','2026-08-28 10:14:20.825326','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(17,NULL,NULL,NULL,'2026-08-28 10:14:57.592455','2026-08-28 10:14:57.409022','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(18,NULL,NULL,NULL,'2026-08-28 10:15:55.687538','2026-08-28 10:15:55.502530','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(19,NULL,NULL,NULL,'2026-08-28 10:16:13.674407','2026-08-28 10:16:13.489405','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(20,NULL,NULL,NULL,'2026-08-28 10:17:08.092369','2026-08-28 10:17:07.909219','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(21,NULL,NULL,NULL,'2026-08-28 12:06:05.320882','2026-08-28 12:06:05.136491','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(22,NULL,NULL,'1','2026-08-28 12:06:05.404824','2026-08-28 12:06:05.391091','凭据','/api/bastion/credential/','{\'name\': \'测试凭据\', \'username\': \'root\', \'auth_type\': \'password\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(23,NULL,NULL,'1','2026-08-28 12:32:31.710639','2026-08-28 12:32:31.696044','服务器','/api/cmdb/server/','{\'ssh_port\': 22, \'status\': \'online\', \'hostname\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\', \'idc\': 1, \'environment\': 2, \'business_line\': 1}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(24,NULL,NULL,'1','2026-08-28 12:33:27.696646','2026-08-28 12:33:27.682376','凭据','/api/bastion/credential/','{\'username\': \'root\', \'auth_type\': \'private_key\', \'name\': \'root\', \'private_key\': \'-----BEGIN OPENSSH PRIVATE KEY-----\\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\\nQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllAAAAJhatzGMWrcx\\njAAAAAtzc2gtZWQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllA\\nAAAECkxEFIcMvV16s/yFxgR1NHz0tMncO+brM2HhFKvcTb7g2cI3x8e+IfplSEJD3XABJb\\n+ltgxDp24qDROAt8E2WUAAAAEnJvb3RAZWNzLTVmYzUtMzMzOAECAw==\\n-----END OPENSSH PRIVATE KEY-----\', \'server\': 1}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(25,NULL,NULL,'1','2026-08-28 12:33:54.295811','2026-08-28 12:33:54.282806','凭据','/api/bastion/credential/2/','{\'username\': \'root\', \'auth_type\': \'password\', \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 12:33:27\', \'update_datetime\': \'2026-08-28 12:33:27\', \'has_password\': False, \'has_private_key\': True, \'server_name\': \'YOUR_SERVER_IP\', \'auth_type_label\': \'私钥\', \'description\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'root\', \'creator\': 1, \'server\': 1, \'password\': \'************\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(26,NULL,NULL,NULL,'2026-08-28 12:40:07.500424','2026-08-28 12:40:07.316876','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(27,NULL,NULL,NULL,'2026-08-28 12:40:22.028031','2026-08-28 12:40:21.844025','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(28,NULL,NULL,NULL,'2026-08-28 12:40:37.769574','2026-08-28 12:40:37.586249','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(29,NULL,NULL,'1','2026-08-28 13:44:42.537167','2026-08-28 13:44:42.521672','凭据','/api/bastion/credential/2/','{\'username\': \'root\', \'auth_type\': \'private_key\', \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 12:33:27\', \'update_datetime\': \'2026-08-28 12:33:54\', \'has_password\': True, \'has_private_key\': True, \'server_name\': \'YOUR_SERVER_IP\', \'auth_type_label\': \'密码\', \'description\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'root\', \'creator\': 1, \'server\': 1, \'private_key\': \'-----BEGIN OPENSSH PRIVATE KEY-----\\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\\nQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllAAAAJhatzGMWrcx\\njAAAAAtzc2gtZWQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllA\\nAAAECkxEFIcMvV16s/yFxgR1NHz0tMncO+brM2HhFKvcTb7g2cI3x8e+IfplSEJD3XABJb\\n+ltgxDp24qDROAt8E2WUAAAAEnJvb3RAZWNzLTVmYzUtMzMzOAECAw==\\n-----END OPENSSH PRIVATE KEY-----\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(30,NULL,NULL,NULL,'2026-08-28 13:48:06.163295','2026-08-28 13:48:05.979566','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(31,NULL,NULL,NULL,'2026-08-28 13:48:20.617658','2026-08-28 13:48:20.432392','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(32,NULL,NULL,NULL,'2026-08-28 13:48:46.494347','2026-08-28 13:48:46.311692','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(33,NULL,NULL,NULL,'2026-08-28 13:49:32.223488','2026-08-28 13:49:32.040390','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(34,NULL,NULL,NULL,'2026-08-28 13:50:56.469189','2026-08-28 13:50:56.285487','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(35,NULL,NULL,NULL,'2026-08-28 13:51:32.224462','2026-08-28 13:51:32.040074','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(36,NULL,NULL,NULL,'2026-08-28 13:51:48.202388','2026-08-28 13:51:48.018716','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(37,NULL,NULL,NULL,'2026-08-28 13:52:52.620912','2026-08-28 13:52:52.432633','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(38,NULL,NULL,'1','2026-08-28 13:56:59.361620','2026-08-28 13:56:59.346181','凭据','/api/bastion/credential/2/','{\'username\': \'root\', \'auth_type\': \'private_key\', \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 12:33:27\', \'update_datetime\': \'2026-08-28 13:44:42\', \'has_password\': True, \'has_private_key\': True, \'server_name\': \'YOUR_SERVER_IP\', \'auth_type_label\': \'私钥\', \'description\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'root\', \'creator\': 1, \'server\': 1, \'private_key\': \'b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\\nQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllAAAAJhatzGMWrcx\\njAAAAAtzc2gtZWQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllA\\nAAAECkxEFIcMvV16s/yFxgR1NHz0tMncO+brM2HhFKvcTb7g2cI3x8e+IfplSEJD3XABJb\\n+ltgxDp24qDROAt8E2WUAAAAEnJvb3RAZWNzLTVmYzUtMzMzOAECAw==\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(39,NULL,NULL,'1','2026-08-28 13:57:48.139889','2026-08-28 13:57:48.122586','凭据','/api/bastion/credential/2/','{\'username\': \'root\', \'auth_type\': \'private_key\', \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 12:33:27\', \'update_datetime\': \'2026-08-28 13:56:59\', \'has_password\': True, \'has_private_key\': True, \'server_name\': \'YOUR_SERVER_IP\', \'auth_type_label\': \'私钥\', \'description\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'root\', \'creator\': 1, \'server\': 1, \'private_key\': \'-----BEGIN OPENSSH PRIVATE KEY-----\\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\\nQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllAAAAJhatzGMWrcx\\njAAAAAtzc2gtZWQyNTUxOQAAACANnCN8fHviH6ZUhCQ91wASW/pbYMQ6duKg0TgLfBNllA\\nAAAECkxEFIcMvV16s/yFxgR1NHz0tMncO+brM2HhFKvcTb7g2cI3x8e+IfplSEJD3XABJb\\n+ltgxDp24qDROAt8E2WUAAAAEnJvb3RAZWNzLTVmYzUtMzMzOAECAw==\\n-----END OPENSSH PRIVATE KEY-----\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(40,NULL,NULL,'1','2026-08-28 14:08:50.914844','2026-08-28 14:08:50.901327','凭据','/api/bastion/credential/2/','{\'username\': \'root\', \'auth_type\': \'password\', \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 12:33:27\', \'update_datetime\': \'2026-08-28 13:57:48\', \'has_password\': True, \'has_private_key\': True, \'server_name\': \'YOUR_SERVER_IP\', \'auth_type_label\': \'私钥\', \'description\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'root\', \'creator\': 1, \'server\': 1, \'password\': \'************\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(41,NULL,NULL,NULL,'2026-08-28 14:11:05.917593','2026-08-28 14:11:05.735498','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(42,NULL,NULL,NULL,'2026-08-28 14:32:13.453294','2026-08-28 14:32:13.270225','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(43,NULL,NULL,'1','2026-08-28 15:07:13.936638','2026-08-28 15:07:13.923944','菜单权限表','/api/system/menu_button/batch_create/','{\'menu\': 3}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'批量创建成功 3 项，跳过 5 项（已存在）\'}',1,1),(44,NULL,NULL,'1','2026-08-28 15:07:24.688647','2026-08-28 15:07:24.681708','菜单权限表','/api/system/menu_button/batch_create/','{\'menu\': 3}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'批量创建成功 0 项，跳过 8 项（已存在）\'}',1,1),(45,NULL,NULL,NULL,'2026-08-28 15:23:50.645336','2026-08-28 15:23:50.450043','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'0\', \'captchaKey\': 7, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Username/password incorrect. Account will be locked after 4 failed attempts~\'}',0,NULL),(46,NULL,NULL,NULL,'2026-08-28 15:24:01.462458','2026-08-28 15:24:01.446844','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'2\', \'captchaKey\': 8, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Image verification code is incorrect\'}',0,NULL),(47,NULL,NULL,'1','2026-08-28 15:24:08.061268','2026-08-28 15:24:07.738277','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'6\', \'captchaKey\': 9, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(48,NULL,NULL,'1','2026-08-28 15:25:31.136371','2026-08-28 15:25:30.852179','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'2\', \'captchaKey\': 10, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(49,NULL,NULL,'1','2026-08-28 15:49:24.765509','2026-08-28 15:49:24.442730','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'3\', \'captchaKey\': 22, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(50,NULL,NULL,NULL,'2026-08-28 15:56:53.221806','2026-08-28 15:56:53.038027','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python Requests 2.31','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(51,NULL,NULL,'1','2026-08-28 15:59:27.373156','2026-08-28 15:59:27.025313','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'9\', \'captchaKey\': 29, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(52,NULL,NULL,'1','2026-08-28 16:01:42.181106','2026-08-28 16:01:42.167927','菜单表','/api/system/menu/move_down/','{\'menu_id\': 18}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Move down successful\'}',1,1),(53,NULL,NULL,'1','2026-08-28 16:01:43.804410','2026-08-28 16:01:43.789688','菜单表','/api/system/menu/move_up/','{\'menu_id\': 18}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Move up successful\'}',1,1),(54,NULL,NULL,'1','2026-08-28 16:20:25.776458','2026-08-28 16:20:25.763837','菜单表','/api/system/menu/17/','{\'parent\': \'\', \'name\': \'定时任务\', \'name_en\': \'Scheduled Tasks\', \'name_zh_tw\': \'定時任務\', \'component\': \'\', \'web_path\': \'/celeryManage\', \'icon\': \'iconfont icon-caijian\', \'cache\': True, \'status\': True, \'visible\': False, \'component_name\': \'\', \'description\': \'\', \'is_catalog\': True, \'is_link\': False, \'is_iframe\': False, \'is_affix\': False, \'link_url\': None, \'id\': 17}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(55,NULL,NULL,'1','2026-08-28 16:20:43.329326','2026-08-28 16:20:43.316565','菜单表','/api/system/menu/17/','{\'parent\': \'\', \'name\': \'定时任务\', \'name_en\': \'Scheduled Tasks\', \'name_zh_tw\': \'定時任務\', \'component\': \'\', \'web_path\': \'/celeryManage\', \'icon\': \'iconfont icon-caijian\', \'cache\': True, \'status\': True, \'visible\': True, \'component_name\': \'\', \'description\': \'\', \'is_catalog\': True, \'is_link\': False, \'is_iframe\': False, \'is_affix\': False, \'link_url\': None, \'id\': 17}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(56,NULL,NULL,NULL,'2026-08-28 16:41:11.004971','2026-08-28 16:41:10.820596','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(57,NULL,NULL,'1','2026-08-28 16:41:11.046733','2026-08-28 16:41:11.037711','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(58,NULL,NULL,NULL,'2026-08-28 16:48:38.983697','2026-08-28 16:48:38.794230','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(59,NULL,NULL,'1','2026-08-28 16:53:46.956032','2026-08-28 16:53:46.943003','Prometheus 数据源','/api/monitor/prometheus/1/','{\'status\': 1, \'sort\': 1, \'id\': 1, \'modifier_name\': None, \'creator_name\': None, \'create_datetime\': \'2026-08-28 16:40:38\', \'update_datetime\': \'2026-08-28 16:40:38\', \'status_label\': \'启用\', \'description\': None, \'modifier\': None, \'dept_belong_id\': None, \'name\': \'本机 Prometheus\', \'url\': \'http://127.0.0.1:9090\', \'creator\': None}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(60,NULL,NULL,'1','2026-08-28 16:54:47.310269','2026-08-28 16:54:47.302576','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(61,NULL,NULL,'1','2026-08-28 16:54:52.911350','2026-08-28 16:54:52.903274','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(62,NULL,NULL,'1','2026-08-28 16:54:53.670177','2026-08-28 16:54:53.662559','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_memory_MemAvailable_bytes\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(63,NULL,NULL,'1','2026-08-28 16:54:54.387185','2026-08-28 16:54:54.380234','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_filesystem_avail_bytes{fstype=~\"ext4|xfs\"}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(64,NULL,NULL,'1','2026-08-28 16:54:54.647601','2026-08-28 16:54:54.640445','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(65,NULL,NULL,'1','2026-08-28 16:54:55.022189','2026-08-28 16:54:55.015224','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_load1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(66,NULL,NULL,'1','2026-08-28 16:54:55.366344','2026-08-28 16:54:55.358273','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(67,NULL,NULL,'1','2026-08-28 16:54:56.385099','2026-08-28 16:54:56.376390','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \'无法连接 Prometheus：http://127.0.0.1:9090\'}',0,1),(68,NULL,NULL,NULL,'2026-08-28 16:55:40.361276','2026-08-28 16:55:40.178426','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(69,NULL,NULL,NULL,'2026-08-28 16:57:18.003724','2026-08-28 16:57:17.820089','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(70,NULL,NULL,'1','2026-08-28 16:57:18.369918','2026-08-28 16:57:18.359238','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(71,NULL,NULL,'1','2026-08-28 16:57:51.578916','2026-08-28 16:57:51.569394','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(72,NULL,NULL,'1','2026-08-28 17:03:30.410523','2026-08-28 17:03:30.398764','Prometheus 数据源','/api/monitor/prometheus/','{\'status\': 1, \'sort\': 1, \'name\': \'生产环境Prometheus\', \'url\': \'http://192.168.0.163:9090\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(73,NULL,NULL,'1','2026-08-28 17:03:41.894878','2026-08-28 17:03:41.885862','Prometheus 数据源','/api/monitor/prometheus/2/','{\'id\': 2}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(74,NULL,NULL,'1','2026-08-28 17:04:01.198825','2026-08-28 17:04:01.190136','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(75,NULL,NULL,'1','2026-08-28 17:04:06.486884','2026-08-28 17:04:06.477635','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(76,NULL,NULL,'1','2026-08-28 17:09:25.965069','2026-08-28 17:09:25.955899','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(77,NULL,NULL,'1','2026-08-28 17:09:52.302617','2026-08-28 17:09:52.291908','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(78,NULL,NULL,'1','2026-08-28 17:09:53.711250','2026-08-28 17:09:53.699526','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(79,NULL,NULL,'1','2026-08-28 17:09:57.202355','2026-08-28 17:09:57.194587','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_load1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(80,NULL,NULL,'1','2026-08-28 17:10:00.413141','2026-08-28 17:10:00.405100','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(81,NULL,NULL,NULL,'2026-08-28 17:22:02.712658','2026-08-28 17:22:02.527651','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(82,NULL,NULL,'1','2026-08-28 17:22:02.737572','2026-08-28 17:22:02.720169','告警规则','/api/alert/rule/','{\'name\': \'测试告警_负载恒真\', \'expr\': \'node_load1 > 0\', \'duration\': \'0s\', \'severity\': \'warning\', \'summary\': \'节点负载告警测试\', \'description\': \'负载大于0（测试链路用）\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(83,NULL,NULL,NULL,'2026-08-28 17:24:12.081640','2026-08-28 17:24:11.895306','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(84,NULL,NULL,'1','2026-08-28 17:24:12.108852','2026-08-28 17:24:12.099643','告警规则','/api/alert/rule/1/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(85,NULL,NULL,NULL,'2026-08-28 17:27:17.499301','2026-08-28 17:27:17.317030','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(86,NULL,NULL,'1','2026-08-28 17:39:07.907162','2026-08-28 17:39:07.893158','告警规则','/api/alert/rule/reload/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'规则已同步并热加载\'}',1,1),(87,NULL,NULL,'1','2026-08-28 17:39:40.965959','2026-08-28 17:39:40.951437','告警规则','/api/alert/rule/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'name\': \'节点宕机告警\', \'expr\': \'up == 0\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(88,NULL,NULL,'1','2026-08-28 17:39:42.705136','2026-08-28 17:39:42.694035','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 0\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(89,NULL,NULL,'1','2026-08-28 17:39:48.444702','2026-08-28 17:39:48.428938','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-28 17:39:40\', \'severity_label\': \'严重\', \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 1\', \'summary\': None, \'description\': None, \'creator\': 1}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(90,NULL,NULL,'1','2026-08-28 17:39:49.142797','2026-08-28 17:39:49.134805','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(91,NULL,NULL,'1','2026-08-28 17:39:52.931734','2026-08-28 17:39:52.923020','告警规则','/api/alert/rule/reload/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'规则已同步并热加载\'}',1,1),(92,NULL,NULL,'1','2026-08-28 17:46:50.541701','2026-08-28 17:46:50.529445','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(93,NULL,NULL,NULL,'2026-08-28 17:52:25.886197','2026-08-28 17:52:25.695392','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(94,NULL,NULL,NULL,'2026-08-28 17:52:51.496928','2026-08-28 17:52:51.314036','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(95,NULL,NULL,'1','2026-08-28 17:52:51.517306','2026-08-28 17:52:51.505208','通知渠道','/api/alert/channel/','{\'name\': \'飞书告警群\', \'type\': \'feishu\', \'config\': {\'webhook\': \'https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN\'}, \'enabled\': True, \'description\': \'测试用飞书群机器人\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(96,NULL,NULL,'1','2026-08-28 17:52:52.048697','2026-08-28 17:52:51.525132','通知渠道','/api/alert/channel/1/test/','{}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'发送成功\'}',1,1),(97,NULL,NULL,'1','2026-08-28 17:52:52.073058','2026-08-28 17:52:52.056808','告警规则','/api/alert/rule/','{\'name\': \'测试通知_负载恒真\', \'expr\': \'node_load1 > 0\', \'duration\': \'0s\', \'severity\': \'warning\', \'summary\': \'节点负载告警测试（验证飞书通知）\', \'description\': \'本告警用于验证 Alertmanager → 平台 webhook → 飞书 的完整链路\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(98,NULL,NULL,'1','2026-08-28 17:53:57.575134','2026-08-28 17:53:57.565990','告警规则','/api/alert/rule/preview/','{\'expr\': \'node_load1 > 0\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(99,NULL,NULL,NULL,'2026-08-28 17:54:15.149515','2026-08-28 17:54:14.963647','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(100,NULL,NULL,'1','2026-08-28 17:54:15.176508','2026-08-28 17:54:15.167806','告警规则','/api/alert/rule/3/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(101,NULL,NULL,'1','2026-08-28 17:54:15.203507','2026-08-28 17:54:15.194345','通知渠道','/api/alert/channel/1/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(102,NULL,NULL,'1','2026-08-28 17:57:05.118001','2026-08-28 17:57:05.107136','通知渠道','/api/alert/channel/','{\'type\': \'feishu\', \'enabled\': True, \'name\': \'运维告警飞书群\', \'config\': \'<div class=\"config-help\" style style=\"color:#909399;font-size:12px;white-space:pre-wrap\">飞书：{\"webhook\":\"https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN\"}</div>\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(103,NULL,NULL,'1','2026-08-28 17:57:09.616964','2026-08-28 17:57:09.610670','通知渠道','/api/alert/channel/2/test/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \"发送异常：\'str\' object has no attribute \'get\'\"}',0,1),(104,NULL,NULL,'1','2026-08-28 17:57:45.369916','2026-08-28 17:57:45.363066','通知渠道','/api/alert/channel/2/test/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','400','Windows 10','{\'code\': 400, \'msg\': \"发送异常：\'str\' object has no attribute \'get\'\"}',0,1),(105,NULL,NULL,'1','2026-08-28 17:57:57.423940','2026-08-28 17:57:57.415994','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(106,NULL,NULL,'1','2026-08-28 17:57:59.775441','2026-08-28 17:57:59.767190','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(107,NULL,NULL,'1','2026-08-28 17:59:00.269134','2026-08-28 17:59:00.261680','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(108,NULL,NULL,NULL,'2026-08-28 18:00:26.204148','2026-08-28 18:00:26.019221','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(109,NULL,NULL,NULL,'2026-08-28 18:00:47.726872','2026-08-28 18:00:47.542773','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(110,NULL,NULL,'1','2026-08-28 18:03:25.085125','2026-08-28 18:03:25.073098','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(111,NULL,NULL,'1','2026-08-28 18:03:37.711197','2026-08-28 18:03:37.269717','通知渠道','/api/alert/channel/2/test/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'发送成功\'}',1,1),(112,NULL,NULL,NULL,'2026-08-28 18:12:03.187499','2026-08-28 18:12:03.004369','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(113,NULL,NULL,'1','2026-08-28 18:12:03.205484','2026-08-28 18:12:03.194905','通知渠道','/api/alert/channel/','{\'name\': \'mock飞书_群组外\', \'type\': \'feishu\', \'config\': {\'webhook\': \'https://open.feishu.cn/open-apis/bot/v2/hook/mock-channel-not-in-group\'}, \'enabled\': True, \'description\': \'用于验证群组路由：此渠道不在任何群组中\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(114,NULL,NULL,'1','2026-08-28 18:12:03.233690','2026-08-28 18:12:03.214991','告警群组','/api/alert/group/','{\'name\': \'测试群组_只含真实飞书\', \'description\': \'验证群组路由分发\', \'enabled\': True, \'channels\': [2]}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(115,NULL,NULL,'1','2026-08-28 18:12:03.256491','2026-08-28 18:12:03.240723','告警规则','/api/alert/rule/','{\'name\': \'测试告警_群组路由\', \'expr\': \'node_load1 > 0\', \'duration\': \'0s\', \'severity\': \'warning\', \'summary\': \'验证群组路由\', \'description\': \'触发后应只发真实飞书，不发 mock\', \'enabled\': True, \'group\': 1}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(116,NULL,NULL,NULL,'2026-08-28 18:12:22.024973','2026-08-28 18:12:21.833170','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(117,NULL,NULL,'1','2026-08-28 18:12:22.053225','2026-08-28 18:12:22.043145','告警规则','/api/alert/rule/4/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(118,NULL,NULL,'1','2026-08-28 18:12:22.081286','2026-08-28 18:12:22.070364','告警规则','/api/alert/rule/1/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','400','Other','{\'code\': 400, \'msg\': \'Endpoint address is incorrect\'}',0,1),(119,NULL,NULL,'1','2026-08-28 18:12:22.105444','2026-08-28 18:12:22.098629','告警规则','/api/alert/rule/3/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','400','Other','{\'code\': 400, \'msg\': \'Endpoint address is incorrect\'}',0,1),(120,NULL,NULL,'1','2026-08-28 18:12:22.135067','2026-08-28 18:12:22.123036','告警群组','/api/alert/group/1/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(121,NULL,NULL,'1','2026-08-28 18:12:22.161270','2026-08-28 18:12:22.151329','通知渠道','/api/alert/channel/3/','{}','DELETE',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(122,NULL,NULL,NULL,'2026-08-31 08:35:23.782945','2026-08-31 08:35:23.767437','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'69\', \'captchaKey\': 30, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Image verification code is incorrect\'}',0,NULL),(123,NULL,NULL,'1','2026-08-31 08:35:26.528897','2026-08-31 08:35:26.175840','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'0\', \'captchaKey\': 31, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(124,NULL,NULL,'1','2026-08-31 08:36:02.728093','2026-08-31 08:36:02.712004','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-28 17:39:48\', \'severity_label\': \'严重\', \'group_name\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': None, \'description\': None, \'creator\': 1, \'group\': None}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(125,NULL,NULL,'1','2026-08-31 08:36:21.149200','2026-08-31 08:36:21.133937','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 08:36:02\', \'severity_label\': \'严重\', \'group_name\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': None, \'description\': None, \'creator\': 1, \'group\': None}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(126,NULL,NULL,'1','2026-08-31 08:36:26.277089','2026-08-31 08:36:25.844651','通知渠道','/api/alert/channel/2/test/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'发送成功\'}',1,1),(127,NULL,NULL,'1','2026-08-31 08:37:32.613353','2026-08-31 08:37:32.598850','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 08:36:21\', \'severity_label\': \'严重\', \'group_name\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': None}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(128,NULL,NULL,'1','2026-08-31 08:41:56.640030','2026-08-31 08:41:56.627176','通知渠道','/api/alert/channel/2/','{\'id\': 2}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(129,NULL,NULL,NULL,'2026-08-31 08:51:27.456514','2026-08-31 08:51:27.272616','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(130,NULL,NULL,'1','2026-08-31 08:51:27.654675','2026-08-31 08:51:27.643609','通知渠道','/api/alert/channel/','{\'name\': \'测试邮箱_验证\', \'type\': \'email\', \'smtp_host\': \'smtp.163.com\', \'smtp_port\': 465, \'smtp_username\': \'your_email@example.com\', \'smtp_password\': \'fakeauthcode\', \'smtp_to\': \'a@163.com, b@163.com\', \'enabled\': True, \'description\': \'验证结构化配置组装\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(131,NULL,NULL,'1','2026-08-31 08:51:27.849091','2026-08-31 08:51:27.838519','通知渠道','/api/alert/channel/','{\'name\': \'测试钉钉_验证\', \'type\': \'dingtalk\', \'webhook\': \'https://oapi.dingtalk.com/robot/send?access_token=testtoken\', \'secret\': \'SECtest123\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(132,NULL,NULL,'1','2026-08-31 08:51:27.863161','2026-08-31 08:51:27.856308','通知渠道','/api/alert/channel/','{\'name\': \'坏渠道\', \'type\': \'feishu\', \'webhook\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': \'config:址\'}',0,1),(133,NULL,NULL,'1','2026-08-31 08:51:27.880581','2026-08-31 08:51:27.869988','通知渠道','/api/alert/channel/4/','{}','DELETE',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(134,NULL,NULL,'1','2026-08-31 08:51:27.897809','2026-08-31 08:51:27.888047','通知渠道','/api/alert/channel/5/','{}','DELETE',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(135,NULL,NULL,NULL,'2026-08-31 08:52:03.650302','2026-08-31 08:52:03.469196','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(136,NULL,NULL,NULL,'2026-08-31 08:52:23.253246','2026-08-31 08:52:23.071208','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(137,NULL,NULL,'1','2026-08-31 08:52:23.266900','2026-08-31 08:52:23.260445','通知渠道','/api/alert/channel/','{\'name\': \'坏渠道\', \'type\': \'feishu\', \'webhook\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': \'config:址\'}',0,1),(138,NULL,NULL,NULL,'2026-08-31 08:53:56.742940','2026-08-31 08:53:56.559054','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(139,NULL,NULL,'1','2026-08-31 08:53:56.925853','2026-08-31 08:53:56.917257','通知渠道','/api/alert/channel/','{\'name\': \'坏渠道\', \'type\': \'feishu\', \'webhook\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': [ErrorDetail(string=\'飞书渠道缺少 Webhook 地址\', code=\'invalid\')]}',0,1),(140,NULL,NULL,'1','2026-08-31 08:53:56.941595','2026-08-31 08:53:56.934410','通知渠道','/api/alert/channel/','{\'name\': \'坏邮箱\', \'type\': \'email\', \'smtp_host\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': [ErrorDetail(string=\'邮箱渠道缺少必填项：SMTP 服务器、发件账号、密码/授权码、收件人\', code=\'invalid\')]}',0,1),(141,NULL,NULL,NULL,'2026-08-31 08:55:21.877766','2026-08-31 08:55:21.694407','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(142,NULL,NULL,'1','2026-08-31 08:55:22.057630','2026-08-31 08:55:22.049073','通知渠道','/api/alert/channel/','{\'name\': \'坏渠道\', \'type\': \'feishu\', \'webhook\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': \'渠道配置:飞书渠道缺少 Webhook 地址\'}',0,1),(143,NULL,NULL,'1','2026-08-31 08:55:22.074700','2026-08-31 08:55:22.067337','通知渠道','/api/alert/channel/','{\'name\': \'坏邮箱\', \'type\': \'email\', \'smtp_host\': \'\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','4000','Other','{\'code\': 4000, \'msg\': \'渠道配置:邮箱渠道缺少必填项：SMTP 服务器、发件账号、密码/授权码、收件人\'}',0,1),(144,NULL,NULL,'1','2026-08-31 08:55:22.091461','2026-08-31 08:55:22.081827','通知渠道','/api/alert/channel/','{\'name\': \'验证飞书\', \'type\': \'feishu\', \'webhook\': \'https://open.feishu.cn/open-apis/bot/v2/hook/testok\', \'enabled\': True}','POST',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(145,NULL,NULL,'1','2026-08-31 08:55:22.109072','2026-08-31 08:55:22.098372','通知渠道','/api/alert/channel/6/','{}','DELETE',NULL,'172.30.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(146,NULL,NULL,'1','2026-08-31 09:49:08.733493','2026-08-31 09:49:08.722580','通知渠道','/api/alert/channel/','{\'type\': \'feishu\', \'smtp_port\': 465, \'enabled\': True, \'webhook\': \'https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_TOKEN\', \'name\': \'飞书告警\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(147,NULL,NULL,'1','2026-08-31 09:52:25.295243','2026-08-31 09:52:25.279491','告警群组','/api/alert/group/','{\'name\': \'测试群组A\', \'channels\': [7], \'enabled\': True, \'description\': \'API测试\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(148,NULL,NULL,'1','2026-08-31 09:52:25.548549','2026-08-31 09:52:25.541034','告警群组','/api/alert/group/','{\'name\': \'测试群组B\', \'channels\': 7, \'enabled\': True, \'description\': \'单值\'}','POST',NULL,'172.30.0.1','curl 8.5.0','4000','Other','{\'code\': 4000, \'msg\': \'通知渠道:期望为一个包含物件的列表，得到的类型是“int”。\'}',0,1),(149,NULL,NULL,'1','2026-08-31 09:52:25.779311','2026-08-31 09:52:25.767621','告警群组','/api/alert/group/','{\'name\': \'测试群组C\', \'enabled\': True}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(150,NULL,NULL,'1','2026-08-31 10:44:14.259968','2026-08-31 10:44:14.244081','告警群组','/api/alert/group/','{\'enabled\': True, \'name\': \'修复验证群组_1788144239\', \'channels\': [7]}','POST',NULL,'127.0.0.1','HeadlessChrome 151.0.7922','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(151,NULL,NULL,'1','2026-08-31 10:44:35.352892','2026-08-31 10:44:35.340664','告警群组','/api/alert/group/4/','{}','DELETE',NULL,'127.0.0.1','Python-urllib 3.13','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(152,NULL,NULL,NULL,'2026-08-31 10:56:56.437781','2026-08-31 10:56:56.254780','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(153,NULL,NULL,NULL,'2026-08-31 10:57:05.429609','2026-08-31 10:57:05.246477','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(154,NULL,NULL,NULL,'2026-08-31 10:57:21.513826','2026-08-31 10:57:21.329689','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(155,NULL,NULL,'1','2026-08-31 11:01:04.441075','2026-08-31 11:01:04.430015','告警群组','/api/alert/group/3/','{\'id\': 3}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(156,NULL,NULL,'1','2026-08-31 11:01:05.796701','2026-08-31 11:01:05.784867','告警群组','/api/alert/group/2/','{\'id\': 2}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(157,NULL,NULL,'1','2026-08-31 11:02:46.137256','2026-08-31 11:02:46.122440','告警群组','/api/alert/group/','{\'enabled\': True, \'name\': \'飞书告警\', \'channels\': [7]}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(158,NULL,NULL,'1','2026-08-31 11:02:59.967681','2026-08-31 11:02:59.949849','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 08:37:32\', \'severity_label\': \'严重\', \'group_name\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': 5}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(159,NULL,NULL,'1','2026-08-31 11:03:01.573031','2026-08-31 11:03:01.566083','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 0\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(160,NULL,NULL,'1','2026-08-31 11:03:06.685626','2026-08-31 11:03:06.225011','通知渠道','/api/alert/channel/7/test/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'发送成功\'}',1,1),(161,NULL,NULL,'1','2026-08-31 11:05:30.141302','2026-08-31 11:05:30.125000','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 11:02:59\', \'severity_label\': \'严重\', \'group_name\': \'飞书告警\', \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 1\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': 5}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(162,NULL,NULL,'1','2026-08-31 11:05:33.546786','2026-08-31 11:05:33.539260','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(163,NULL,NULL,'1','2026-08-31 11:06:12.427438','2026-08-31 11:06:12.418904','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(164,NULL,NULL,'1','2026-08-31 11:07:43.712376','2026-08-31 11:07:43.704579','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(165,NULL,NULL,'1','2026-08-31 11:08:02.156789','2026-08-31 11:08:02.149157','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_memory_MemAvailable_bytes\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(166,NULL,NULL,'1','2026-08-31 11:08:03.178806','2026-08-31 11:08:03.168853','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'node_memory_MemAvailable_bytes\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(167,NULL,NULL,'1','2026-08-31 11:15:05.738056','2026-08-31 11:15:05.722368','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 11:05:30\', \'severity_label\': \'严重\', \'group_name\': \'飞书告警\', \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': 5}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(168,NULL,NULL,NULL,'2026-08-31 11:30:29.371813','2026-08-31 11:30:29.186451','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(169,NULL,NULL,'1','2026-08-31 11:35:37.177101','2026-08-31 11:35:37.158268','命令下发','/api/bastion/dispatch/','{\'name\': \'x\', \'command\': \'uptime\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'x\', \'ip\': \'YOUR_SERVER_IP\', \'ssh_port\': 22}], \'timeout\': 30}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(170,NULL,NULL,'1','2026-08-31 11:35:48.606788','2026-08-31 11:35:48.375906','命令下发','/api/bastion/dispatch/1/execute/','{\'max_workers\': 5}','POST',NULL,'172.30.0.1','curl 8.5.0','2000','Other','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(171,NULL,NULL,'1','2026-08-31 11:44:08.414705','2026-08-31 11:44:08.397698','命令下发','/api/bastion/dispatch/','{\'name\': \'查看内存\', \'command\': \'free -h\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\', \'ssh_port\': 22}], \'timeout\': 30}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(172,NULL,NULL,NULL,'2026-08-31 11:48:00.911198','2026-08-31 11:48:00.725847','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','curl 8.21.0','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(173,NULL,NULL,NULL,'2026-08-31 11:48:22.284147','2026-08-31 11:48:22.101320','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(174,NULL,NULL,NULL,'2026-08-31 11:48:33.717595','2026-08-31 11:48:33.534965','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(175,NULL,NULL,NULL,'2026-08-31 11:53:28.864430','2026-08-31 11:53:28.683719','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(176,NULL,NULL,NULL,'2026-08-31 11:54:20.463389','2026-08-31 11:54:20.279660','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(177,NULL,NULL,NULL,'2026-08-31 11:54:53.778112','2026-08-31 11:54:53.591901','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(178,NULL,NULL,NULL,'2026-08-31 11:56:19.415944','2026-08-31 11:56:19.234853','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(179,NULL,NULL,NULL,'2026-08-31 11:57:32.310099','2026-08-31 11:57:32.128856','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(180,NULL,NULL,NULL,'2026-08-31 11:59:21.261335','2026-08-31 11:59:21.078226','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(181,NULL,NULL,NULL,'2026-08-31 11:59:44.909458','2026-08-31 11:59:44.728340','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(182,NULL,NULL,NULL,'2026-08-31 12:00:20.553157','2026-08-31 12:00:20.370434','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(183,NULL,NULL,NULL,'2026-08-31 12:03:27.805034','2026-08-31 12:03:27.624844','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(184,NULL,NULL,'1','2026-08-31 12:03:41.660963','2026-08-31 12:03:41.124172','命令下发','/api/bastion/dispatch/2/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','HeadlessChrome 151.0.7922','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(185,NULL,NULL,NULL,'2026-08-31 12:06:06.240442','2026-08-31 12:06:06.058761','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(186,NULL,NULL,'1','2026-08-31 12:06:20.414133','2026-08-31 12:06:19.905453','命令下发','/api/bastion/dispatch/2/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','HeadlessChrome 151.0.7922','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(187,NULL,NULL,NULL,'2026-08-31 12:11:53.948299','2026-08-31 12:11:53.766678','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(188,NULL,NULL,'1','2026-08-31 12:12:08.468443','2026-08-31 12:12:07.965043','命令下发','/api/bastion/dispatch/2/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','HeadlessChrome 151.0.7922','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(189,NULL,NULL,'1','2026-08-31 13:21:55.477249','2026-08-31 13:21:55.458518','命令下发','/api/bastion/dispatch/','{\'name\': \'查看磁盘使用\', \'command\': \'df -h\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\', \'ssh_port\': 22}], \'timeout\': 30}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(190,NULL,NULL,'1','2026-08-31 13:22:15.721844','2026-08-31 13:22:15.412325','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'27\', \'captchaKey\': 75, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(191,NULL,NULL,NULL,'2026-08-31 13:25:43.255330','2026-08-31 13:25:43.073905','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(192,NULL,NULL,NULL,'2026-08-31 13:29:22.965498','2026-08-31 13:29:22.784644','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(193,NULL,NULL,NULL,'2026-08-31 13:29:59.176188','2026-08-31 13:29:58.995796','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(194,NULL,NULL,NULL,'2026-08-31 13:32:31.934686','2026-08-31 13:32:31.747921','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.34','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(195,NULL,NULL,'1','2026-08-31 13:34:27.787508','2026-08-31 13:34:27.246417','命令下发','/api/bastion/dispatch/3/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(196,NULL,NULL,'1','2026-08-31 13:34:39.704723','2026-08-31 13:34:39.477138','命令下发','/api/bastion/dispatch/2/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(197,NULL,NULL,'1','2026-08-31 13:34:42.919493','2026-08-31 13:34:42.696514','命令下发','/api/bastion/dispatch/1/execute/','{\'max_workers\': 10}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(198,NULL,NULL,NULL,'2026-08-31 13:53:26.955267','2026-08-31 13:53:26.768741','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(199,NULL,NULL,NULL,'2026-08-31 13:53:38.707316','2026-08-31 13:53:38.519566','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(200,NULL,NULL,NULL,'2026-08-31 13:54:04.547197','2026-08-31 13:54:03.848674','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(201,NULL,NULL,'1','2026-08-31 13:54:04.621188','2026-08-31 13:54:04.593677','命令下发','/api/bastion/dispatch/','{\'name\': \'P34验证_审计重试\', \'command\': \'uptime\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\'}, {\'server_id\': None, \'label\': \'假IP\', \'ip\': \'10.99.99.99\'}], \'timeout\': 15, \'max_workers\': 5}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(202,NULL,NULL,'1','2026-08-31 13:54:14.692884','2026-08-31 13:54:04.635405','命令下发','/api/bastion/dispatch/4/execute/','{}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(203,NULL,NULL,'1','2026-08-31 13:54:24.771755','2026-08-31 13:54:14.719855','命令下发','/api/bastion/dispatch/4/execute/','{\'retry\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(204,NULL,NULL,'1','2026-08-31 13:54:24.802863','2026-08-31 13:54:24.782819','命令下发','/api/bastion/dispatch/','{\'name\': \'P34验证_高危标记\', \'command\': \'echo rm -rf test\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\'}], \'timeout\': 15, \'max_workers\': 5}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(205,NULL,NULL,'1','2026-08-31 13:54:25.428216','2026-08-31 13:54:24.813219','命令下发','/api/bastion/dispatch/5/execute/','{}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(206,NULL,NULL,NULL,'2026-08-31 13:56:15.510784','2026-08-31 13:56:15.327896','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(207,NULL,NULL,NULL,'2026-08-31 13:56:33.808483','2026-08-31 13:56:33.624431','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(208,NULL,NULL,NULL,'2026-08-31 13:59:00.433943','2026-08-31 13:59:00.249519','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(209,NULL,NULL,'1','2026-08-31 13:59:14.743099','2026-08-31 13:59:14.725291','命令下发','/api/bastion/dispatch/','{\'name\': \'P34高危验证\', \'command\': \'echo rm -rf test\', \'credential\': 2, \'targets\': [{\'server_id\': 1, \'label\': \'YOUR_SERVER_IP\', \'ip\': \'YOUR_SERVER_IP\', \'ssh_port\': 22}], \'timeout\': 30, \'max_workers\': 10}','POST',NULL,'127.0.0.1','HeadlessChrome 151.0.7922','2000','Windows 10','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(210,NULL,NULL,NULL,'2026-08-31 14:18:02.353831','2026-08-31 14:18:02.168185','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(211,NULL,NULL,NULL,'2026-08-31 14:18:31.841060','2026-08-31 14:18:31.658458','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(212,NULL,NULL,NULL,'2026-08-31 14:19:58.973909','2026-08-31 14:19:58.789357','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(213,NULL,NULL,NULL,'2026-08-31 14:20:46.041554','2026-08-31 14:20:45.857611','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(214,NULL,NULL,'1','2026-08-31 14:20:46.074436','2026-08-31 14:20:46.056415','命令下发','/api/bastion/dispatch/','{\'name\': \'ssh_port验证_手动IP端口\', \'command\': \'uptime\', \'credential\': 2, \'targets\': [{\'server_id\': None, \'label\': \'10.99.99.99\', \'ip\': \'10.99.99.99\', \'ssh_port\': 2222}, {\'server_id\': None, \'label\': \'10.88.88.88\', \'ip\': \'10.88.88.88\', \'ssh_port\': 2223}], \'timeout\': 15, \'max_workers\': 5}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(215,NULL,NULL,'1','2026-08-31 14:26:10.426598','2026-08-31 14:26:10.413341','命令下发','/api/bastion/dispatch/6/','{\'id\': 6}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(216,NULL,NULL,'1','2026-08-31 14:26:12.937701','2026-08-31 14:26:12.924614','命令下发','/api/bastion/dispatch/5/','{\'id\': 5}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(217,NULL,NULL,'1','2026-08-31 14:26:27.712402','2026-08-31 14:26:17.678324','命令下发','/api/bastion/dispatch/4/execute/','{\'retry\': True}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(218,NULL,NULL,'1','2026-08-31 14:26:29.917691','2026-08-31 14:26:19.881202','命令下发','/api/bastion/dispatch/4/execute/','{\'retry\': False}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(219,NULL,NULL,'1','2026-08-31 14:26:38.931347','2026-08-31 14:26:38.920578','命令下发','/api/bastion/dispatch/4/','{\'id\': 4}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(220,NULL,NULL,'1','2026-08-31 14:26:41.993764','2026-08-31 14:26:41.764915','命令下发','/api/bastion/dispatch/3/execute/','{\'retry\': False}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'执行完成\'}',1,1),(221,NULL,NULL,'1','2026-08-31 14:27:06.068818','2026-08-31 14:27:06.057060','命令下发','/api/bastion/dispatch/1/','{\'id\': 1}','DELETE',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(222,NULL,NULL,'1','2026-08-31 14:29:10.870360','2026-08-31 14:29:10.861028','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(223,NULL,NULL,'1','2026-08-31 14:43:31.827819','2026-08-31 14:43:31.819864','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(224,NULL,NULL,'1','2026-08-31 15:00:38.221645','2026-08-31 15:00:38.210974','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(225,NULL,NULL,NULL,'2026-08-31 15:13:31.550973','2026-08-31 15:13:31.365733','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(226,NULL,NULL,NULL,'2026-08-31 15:14:30.080903','2026-08-31 15:14:29.893111','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(227,NULL,NULL,NULL,'2026-08-31 15:21:01.020865','2026-08-31 15:21:00.835193','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(228,NULL,NULL,NULL,'2026-08-31 15:30:50.429809','2026-08-31 15:30:50.244386','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(229,NULL,NULL,NULL,'2026-08-31 15:34:40.781374','2026-08-31 15:34:40.766778','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'14\', \'captchaKey\': 84, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Electron 37.10.3','4000','Windows 10','{\'code\': 4000, \'msg\': \'Verification code has expired\'}',0,NULL),(230,NULL,NULL,NULL,'2026-08-31 15:34:44.300259','2026-08-31 15:34:44.108238','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'7\', \'captchaKey\': 86, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Electron 37.10.3','4000','Windows 10','{\'code\': 4000, \'msg\': \'Username/password incorrect. Account will be locked after 4 failed attempts~\'}',0,NULL),(231,NULL,NULL,NULL,'2026-08-31 15:35:30.420278','2026-08-31 15:35:30.408939','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'72\', \'captchaKey\': 87, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Electron 37.10.3','4000','Windows 10','{\'code\': 4000, \'msg\': \'Image verification code is incorrect\'}',0,NULL),(232,NULL,NULL,'1','2026-08-31 15:38:42.039580','2026-08-31 15:38:42.025164','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(233,NULL,NULL,NULL,'2026-08-31 15:39:41.967501','2026-08-31 15:39:41.784541','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(234,NULL,NULL,'1','2026-08-31 15:42:15.773979','2026-08-31 15:42:15.710445','告警规则','/api/alert/rule/reload/','{}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'规则已同步并热加载\'}',1,1),(235,NULL,NULL,'1','2026-08-31 15:42:20.562506','2026-08-31 15:42:20.551751','Prometheus 数据源','/api/monitor/prometheus/1/query/','{\'query\': \'up\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(236,NULL,NULL,NULL,'2026-08-31 15:54:11.656706','2026-08-31 15:54:11.470930','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(237,NULL,NULL,'1','2026-08-31 15:54:11.859744','2026-08-31 15:54:11.844411','告警模板','/api/alert/template/','{\'name\': \'默认模板\', \'description\': \'默认兜底模板\', \'body\': \'[DevOps] {{ alertname }} ({{ status }})\\n级别：{{ severity | upper }}\\n实例：{{ instance }}\\n摘要：{{ summary }}\\n\', \'is_default\': True, \'enabled\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(238,NULL,NULL,'1','2026-08-31 15:54:11.892945','2026-08-31 15:54:11.878133','告警模板','/api/alert/template/','{\'name\': \'规则专属模板\', \'description\': \'绑定到具体规则的模板\', \'body\': \'【{{ severity | upper }}】{{ alertname }} ({{ status }})\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}{% endif %}\\n\', \'enabled\': True, \'rule\': 2}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(239,NULL,NULL,'1','2026-08-31 15:54:11.906923','2026-08-31 15:54:11.901243','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname }} from {{ instance }} status={{ status }}\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(240,NULL,NULL,'1','2026-08-31 15:54:11.919364','2026-08-31 15:54:11.913701','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','400','Other','{\'code\': 400, \'msg\': \"模板语法错误：unexpected end of template, expected \'end of print statement\'.\"}',0,1),(241,NULL,NULL,NULL,'2026-08-31 15:54:42.882932','2026-08-31 15:54:42.700038','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(242,NULL,NULL,NULL,'2026-08-31 15:55:08.016993','2026-08-31 15:55:07.833828','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(243,NULL,NULL,'1','2026-08-31 15:55:08.072975','2026-08-31 15:55:08.058707','告警模板','/api/alert/template/','{\'name\': \'默认模板\', \'description\': \'默认兜底模板\', \'body\': \'[DevOps] {{ alertname }} ({{ status }})\\n级别：{{ severity | upper }}\\n实例：{{ instance }}\\n摘要：{{ summary }}\\n\', \'is_default\': True, \'enabled\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(244,NULL,NULL,'1','2026-08-31 15:55:08.103980','2026-08-31 15:55:08.091293','告警模板','/api/alert/template/','{\'name\': \'规则专属模板\', \'description\': \'绑定到具体规则的模板\', \'body\': \'【{{ severity | upper }}】{{ alertname }} ({{ status }})\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}{% endif %}\\n\', \'enabled\': True, \'rule\': 2}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(245,NULL,NULL,'1','2026-08-31 15:55:08.116798','2026-08-31 15:55:08.110958','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname }} from {{ instance }} status={{ status }}\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(246,NULL,NULL,'1','2026-08-31 15:55:08.128664','2026-08-31 15:55:08.123787','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','400','Other','{\'code\': 400, \'msg\': \"模板语法错误：unexpected end of template, expected \'end of print statement\'.\"}',0,1),(247,NULL,NULL,'1','2026-08-31 15:55:08.149811','2026-08-31 15:55:08.135823','告警模板','/api/alert/template/3/','{\'id\': 3, \'name\': \'默认模板\', \'description\': \'已修改\', \'body\': \'{{ alertname }} v2\', \'is_default\': True, \'enabled\': True}','PUT',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(248,NULL,NULL,'1','2026-08-31 15:55:08.163057','2026-08-31 15:55:08.156606','告警模板','/api/alert/template/','{\'name\': \'默认模板\', \'body\': \'x\', \'is_default\': False, \'enabled\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','4000','Other','{\'code\': 4000, \'msg\': \'模板名称:具有 模板名称 的 告警模板 已存在。\'}',0,1),(249,NULL,NULL,NULL,'2026-08-31 15:55:31.709519','2026-08-31 15:55:31.524745','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(250,NULL,NULL,'1','2026-08-31 15:55:31.761132','2026-08-31 15:55:31.748392','告警模板','/api/alert/template/','{\'name\': \'默认模板\', \'description\': \'默认兜底模板\', \'body\': \'[DevOps] {{ alertname }} ({{ status }})\\n级别：{{ severity | upper }}\\n实例：{{ instance }}\\n摘要：{{ summary }}\\n\', \'is_default\': True, \'enabled\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(251,NULL,NULL,'1','2026-08-31 15:55:31.792926','2026-08-31 15:55:31.778878','告警模板','/api/alert/template/','{\'name\': \'规则专属模板\', \'description\': \'绑定到具体规则的模板\', \'body\': \'【{{ severity | upper }}】{{ alertname }} ({{ status }})\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}{% endif %}\\n\', \'enabled\': True, \'rule\': 2}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(252,NULL,NULL,'1','2026-08-31 15:55:31.806516','2026-08-31 15:55:31.799890','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname }} from {{ instance }} status={{ status }}\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(253,NULL,NULL,'1','2026-08-31 15:55:31.817833','2026-08-31 15:55:31.813313','告警模板','/api/alert/template/preview/','{\'body\': \'Hi {{ alertname\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','400','Other','{\'code\': 400, \'msg\': \"模板语法错误：unexpected end of template, expected \'end of print statement\'.\"}',0,1),(254,NULL,NULL,'1','2026-08-31 15:55:31.838787','2026-08-31 15:55:31.824724','告警模板','/api/alert/template/5/','{\'id\': 5, \'name\': \'默认模板\', \'description\': \'已修改\', \'body\': \'{{ alertname }} v2\', \'is_default\': True, \'enabled\': True}','PUT',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(255,NULL,NULL,'1','2026-08-31 15:55:31.852189','2026-08-31 15:55:31.845756','告警模板','/api/alert/template/','{\'name\': \'默认模板\', \'body\': \'x\', \'is_default\': False, \'enabled\': True}','POST',NULL,'127.0.0.1','Python Requests 2.32','4000','Other','{\'code\': 4000, \'msg\': \'模板名称:具有 模板名称 的 告警模板 已存在。\'}',0,1),(256,NULL,NULL,'1','2026-08-31 15:55:31.890043','2026-08-31 15:55:31.881632','告警模板','/api/alert/template/5/','{}','DELETE',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(257,NULL,NULL,'1','2026-08-31 15:55:31.906359','2026-08-31 15:55:31.896997','告警模板','/api/alert/template/6/','{}','DELETE',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(258,NULL,NULL,NULL,'2026-08-31 16:01:09.044897','2026-08-31 16:01:08.859414','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(259,NULL,NULL,NULL,'2026-08-31 16:01:11.123416','2026-08-31 16:01:10.935494','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(260,NULL,NULL,NULL,'2026-08-31 16:02:36.568323','2026-08-31 16:02:36.383296','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(261,NULL,NULL,NULL,'2026-08-31 16:03:15.680460','2026-08-31 16:03:15.495788','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(262,NULL,NULL,NULL,'2026-08-31 16:04:11.150224','2026-08-31 16:04:10.965697','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(263,NULL,NULL,NULL,'2026-08-31 16:05:10.449887','2026-08-31 16:05:10.266361','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(264,NULL,NULL,NULL,'2026-08-31 16:06:23.160817','2026-08-31 16:06:22.978522','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(265,NULL,NULL,NULL,'2026-08-31 16:07:14.461636','2026-08-31 16:07:14.278929','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(266,NULL,NULL,NULL,'2026-08-31 16:07:52.609153','2026-08-31 16:07:52.423219','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(267,NULL,NULL,NULL,'2026-08-31 16:08:21.407237','2026-08-31 16:08:21.225019','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(268,NULL,NULL,NULL,'2026-08-31 16:08:44.597867','2026-08-31 16:08:44.413188','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(269,NULL,NULL,NULL,'2026-08-31 16:12:58.194998','2026-08-31 16:12:58.100369','','/api/token/','{\'username\': \'x\', \'password\': \'*\'}','POST',NULL,'172.30.0.1','curl 8.5.0','401','Other','{\'code\': 401, \'msg\': ErrorDetail(string=\'账号/密码不正确\', code=\'no_active_account\')}',0,NULL),(270,NULL,NULL,'1','2026-08-31 16:14:55.632522','2026-08-31 16:14:55.625782','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】{{ alertname }}\\n实例：{{ instance }}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(271,NULL,NULL,'1','2026-08-31 16:15:20.388666','2026-08-31 16:15:20.382565','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】{{ alertname }}\\n实例：{{ instance }}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(272,NULL,NULL,'1','2026-08-31 16:15:28.332217','2026-08-31 16:15:28.325350','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】{{ alertname }}\\n实例：{{ instance }}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(273,NULL,NULL,'1','2026-08-31 16:15:43.149777','2026-08-31 16:15:43.141136','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 0\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(274,NULL,NULL,'1','2026-08-31 16:15:51.156159','2026-08-31 16:15:51.150285','告警模板','/api/alert/template/preview/','{\'body\': \'[DevOps] {{ alertname }} ({{ status }})\\n级别：{{ severity }}\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(275,NULL,NULL,NULL,'2026-08-31 16:16:15.292624','2026-08-31 16:16:15.108447','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(276,NULL,NULL,NULL,'2026-08-31 16:20:28.053404','2026-08-31 16:20:27.869895','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(277,NULL,NULL,NULL,'2026-08-31 16:21:21.049375','2026-08-31 16:21:20.864549','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(278,NULL,NULL,NULL,'2026-08-31 16:22:18.061979','2026-08-31 16:22:17.871125','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(279,NULL,NULL,NULL,'2026-08-31 16:24:32.530705','2026-08-31 16:24:32.346572','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(280,NULL,NULL,NULL,'2026-08-31 16:25:28.457964','2026-08-31 16:25:28.272864','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(281,NULL,NULL,NULL,'2026-08-31 16:25:52.835369','2026-08-31 16:25:52.652516','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(282,NULL,NULL,NULL,'2026-08-31 16:27:33.382420','2026-08-31 16:27:33.199458','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(283,NULL,NULL,NULL,'2026-08-31 16:29:32.639013','2026-08-31 16:29:32.452942','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(284,NULL,NULL,NULL,'2026-08-31 16:29:52.844005','2026-08-31 16:29:52.661644','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(285,NULL,NULL,NULL,'2026-08-31 16:33:42.081107','2026-08-31 16:33:41.895869','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(286,NULL,NULL,NULL,'2026-08-31 16:34:16.776354','2026-08-31 16:34:16.587215','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(287,NULL,NULL,NULL,'2026-08-31 16:37:22.037105','2026-08-31 16:37:21.848547','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(288,NULL,NULL,'1','2026-08-31 17:32:32.068721','2026-08-31 17:32:32.054976','系统配置表','/api/system/system_config/4/','{\'id\': 4, \'value\': False}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(289,NULL,NULL,'1','2026-08-31 17:32:41.466265','2026-08-31 17:32:41.139873','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'11\', \'captchaKey\': 107, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1),(290,NULL,NULL,'1','2026-08-31 17:32:44.285094','2026-08-31 17:32:44.272432','系统配置表','/api/system/system_config/4/','{\'id\': 4, \'value\': True}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(291,NULL,NULL,'1','2026-08-31 17:33:08.798911','2026-08-31 17:33:08.786345','系统配置表','/api/system/system_config/13/','{\'id\': 13, \'value\': \'https://django-vue-admin.com\'}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(292,NULL,NULL,NULL,'2026-08-31 17:42:58.670712','2026-08-31 17:42:58.483106','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(293,NULL,NULL,NULL,'2026-08-31 17:44:03.095702','2026-08-31 17:44:02.902733','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(294,NULL,NULL,'1','2026-08-31 17:44:03.129608','2026-08-31 17:44:03.113016','告警规则','/api/alert/rule/','{\'name\': \'__test_rule_tpl\', \'expr\': \'up == 0\', \'duration\': \'1m\', \'severity\': \'warning\', \'summary\': \'关联模板测试\', \'description\': \'\', \'enabled\': True, \'template\': 36}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Create successful\'}',1,1),(295,NULL,NULL,'1','2026-08-31 17:44:03.175048','2026-08-31 17:44:03.158637','告警规则','/api/alert/rule/6/','{\'id\': 6, \'name\': \'__test_rule_tpl\', \'expr\': \'up == 0\', \'duration\': \'1m\', \'severity\': \'warning\', \'summary\': \'关联模板测试\', \'description\': \'\', \'enabled\': True, \'template\': 35}','PUT',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(296,NULL,NULL,'1','2026-08-31 17:44:03.197460','2026-08-31 17:44:03.183009','告警规则','/api/alert/rule/6/','{\'id\': 6, \'name\': \'__test_rule_tpl\', \'expr\': \'up == 0\', \'duration\': \'1m\', \'severity\': \'warning\', \'summary\': \'关联模板测试\', \'description\': \'\', \'enabled\': True, \'template\': None}','PUT',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(297,NULL,NULL,'1','2026-08-31 17:44:03.215184','2026-08-31 17:44:03.205493','告警规则','/api/alert/rule/6/','{}','DELETE',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Delete successful\'}',1,1),(298,NULL,NULL,NULL,'2026-08-31 17:44:51.284751','2026-08-31 17:44:51.082640','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(299,NULL,NULL,NULL,'2026-08-31 17:50:44.122772','2026-08-31 17:50:43.938094','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(300,NULL,NULL,NULL,'2026-08-31 17:56:47.440469','2026-08-31 17:56:47.255605','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(301,NULL,NULL,NULL,'2026-08-31 18:05:08.611288','2026-08-31 18:05:08.424106','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(302,NULL,NULL,NULL,'2026-08-31 18:05:53.087796','2026-08-31 18:05:52.904132','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python-urllib 3.12','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(303,NULL,NULL,NULL,'2026-08-31 18:13:01.411933','2026-08-31 18:13:01.222934','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(304,NULL,NULL,NULL,'2026-08-31 18:14:41.508674','2026-08-31 18:14:41.325636','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(305,NULL,NULL,NULL,'2026-08-31 18:18:44.441937','2026-08-31 18:18:44.257363','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(306,NULL,NULL,'1','2026-08-31 18:19:37.327347','2026-08-31 18:19:37.319462','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】服务健康告警：{{ alertname }}\\n实例：{{ instance }}\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if value %}当前值：{{ value }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(307,NULL,NULL,NULL,'2026-08-31 18:19:40.014953','2026-08-31 18:19:39.829497','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(308,NULL,NULL,'1','2026-08-31 18:19:56.184710','2026-08-31 18:19:56.091362','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 11:15:05\', \'severity_label\': \'严重\', \'group_name\': \'飞书告警\', \'template_name\': None, \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 1\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': 5, \'template\': 39}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(309,NULL,NULL,'1','2026-08-31 18:19:57.053846','2026-08-31 18:19:57.036196','告警规则','/api/alert/rule/preview/','{\'expr\': \'up == 1\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'查询成功\'}',1,1),(310,NULL,NULL,'1','2026-08-31 18:20:16.736150','2026-08-31 18:20:16.729749','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】主机宕机告警：{{ alertname }}\\n实例：{{ instance }}\\n状态：{{ status }}\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(311,NULL,NULL,'1','2026-08-31 18:21:53.914089','2026-08-31 18:21:53.907863','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】主机宕机告警：{{ alertname }}\\n实例：{{ instance }}\\n状态：{{ status }}\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(312,NULL,NULL,'1','2026-08-31 18:22:06.784642','2026-08-31 18:22:06.778157','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】CPU 使用率告警：{{ alertname }}\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}\\n{% endif %}{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(313,NULL,NULL,'1','2026-08-31 18:22:09.079212','2026-08-31 18:22:09.072667','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】内存使用率告警：{{ alertname }}\\n实例：{{ instance }}\\n{% if value %}当前值：{{ value }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(314,NULL,NULL,'1','2026-08-31 18:22:11.344550','2026-08-31 18:22:11.338265','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】主机宕机告警：{{ alertname }}\\n实例：{{ instance }}\\n状态：{{ status }}\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(315,NULL,NULL,'1','2026-08-31 18:22:21.253642','2026-08-31 18:22:21.246028','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】服务健康告警：{{ alertname }}\\n实例：{{ instance }}\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if value %}当前值：{{ value }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(316,NULL,NULL,'1','2026-08-31 18:22:24.372997','2026-08-31 18:22:24.342144','告警模板','/api/alert/template/preview/','{\'body\': \'【{{ severity | upper }}】{{ alertname }} ({{ status }})\\n{% if summary %}摘要：{{ summary }}\\n{% endif %}{% if description %}描述：{{ description }}\\n{% endif %}{% if instance %}实例：{{ instance }}\\n{% endif %}{% if value %}当前值：{{ value }}\\n{% endif %}{% if startsAt %}开始时间：{{ startsAt }}\\n{% endif %}\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'渲染成功\'}',1,1),(317,NULL,NULL,'1','2026-08-31 18:22:45.350197','2026-08-31 18:22:45.332092','告警规则','/api/alert/rule/2/','{\'duration\': \'1m\', \'severity\': \'critical\', \'enabled\': True, \'id\': 2, \'modifier_name\': \'超级管理员\', \'creator_name\': \'超级管理员\', \'create_datetime\': \'2026-08-28 17:39:40\', \'update_datetime\': \'2026-08-31 18:19:56\', \'severity_label\': \'严重\', \'group_name\': \'飞书告警\', \'template_name\': \'节点宕机（主机不可达）\', \'modifier\': \'1\', \'dept_belong_id\': \'1\', \'name\': \'节点宕机告警\', \'expr\': \'up == 0\', \'summary\': \'服务器宕机\', \'description\': \'服务器宕机\', \'creator\': 1, \'group\': 5, \'template\': 39}','PUT',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Update successful\'}',1,1),(318,NULL,NULL,NULL,'2026-08-31 18:35:58.395107','2026-08-31 18:35:58.206270','','/api/token/','{\'username\': \'superadmin\', \'password\': \'************\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','401','Other','{\'code\': 401, \'msg\': ErrorDetail(string=\'账号/密码不正确\', code=\'no_active_account\')}',0,NULL),(319,NULL,NULL,NULL,'2026-08-31 18:40:42.808222','2026-08-31 18:40:42.614849','','/api/token/','{\'username\': \'superadmin\', \'password\': \'**********************\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(320,NULL,NULL,NULL,'2026-08-31 18:40:42.998069','2026-08-31 18:40:42.817258','','/api/token/','{\'username\': \'superadmin\', \'password\': \'***********\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','401','Other','{\'code\': 401, \'msg\': ErrorDetail(string=\'账号/密码不正确\', code=\'no_active_account\')}',0,NULL),(321,NULL,NULL,NULL,'2026-08-31 18:41:49.721404','2026-08-31 18:41:49.532425','','/api/token/','{\'username\': \'superadmin\', \'password\': \'**********************\'}','POST',NULL,'127.0.0.1','Python Requests 2.32','2000','Other','{\'code\': 2000, \'msg\': \'Request successful\'}',1,NULL),(322,NULL,NULL,NULL,'2026-09-01 08:24:57.948562','2026-09-01 08:24:57.756515','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'1\', \'captchaKey\': 116, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','4000','Windows 10','{\'code\': 4000, \'msg\': \'Username/password incorrect. Account will be locked after 4 failed attempts~\'}',0,NULL),(323,NULL,NULL,'1','2026-09-01 08:25:03.110854','2026-09-01 08:25:02.792765','登录模块','/api/login/','{\'username\': \'superadmin\', \'password\': \'********************************\', \'captcha\': \'8\', \'captchaKey\': 117, \'captchaImgBase\': \'data:image/png;base64,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\'}','POST',NULL,'127.0.0.1','Chrome 151.0.0','2000','Windows 10','{\'code\': 2000, \'msg\': \'Request successful\'}',1,1);
/*!40000 ALTER TABLE `dvadmin_system_operation_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_post`
--

DROP TABLE IF EXISTS `dvadmin_system_post`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_post` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `code` varchar(32) NOT NULL,
  `sort` int NOT NULL,
  `status` int NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dvadmin_system_post_creator_id_b5ef9351` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_post`
--

LOCK TABLES `dvadmin_system_post` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_post` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_post` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_role`
--

DROP TABLE IF EXISTS `dvadmin_system_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `key` varchar(64) NOT NULL,
  `sort` int NOT NULL,
  `status` tinyint(1) NOT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`),
  KEY `dvadmin_system_role_creator_id_a89a9bc7` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_role`
--

LOCK TABLES `dvadmin_system_role` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_role` DISABLE KEYS */;
INSERT INTO `dvadmin_system_role` VALUES (1,NULL,NULL,NULL,'2026-08-27 18:04:38.888843','2026-08-27 18:04:38.888854','管理员','admin',1,1,NULL),(2,NULL,NULL,NULL,'2026-08-27 18:04:38.892661','2026-08-27 18:04:38.892672','用户','public',2,1,NULL),(3,NULL,NULL,NULL,'2026-08-28 15:17:42.907558','2026-08-28 15:17:42.907579','超级管理员','super_admin',1,1,NULL);
/*!40000 ALTER TABLE `dvadmin_system_role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users`
--

DROP TABLE IF EXISTS `dvadmin_system_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users` (
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `username` varchar(150) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `mobile` varchar(255) DEFAULT NULL,
  `avatar` varchar(255) DEFAULT NULL,
  `name` varchar(40) NOT NULL,
  `gender` int DEFAULT NULL,
  `user_type` int DEFAULT NULL,
  `login_error_count` int NOT NULL,
  `pwd_change_count` int NOT NULL,
  `language` varchar(10) DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  `current_role_id` bigint DEFAULT NULL,
  `dept_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `dvadmin_system_users_creator_id_28556713` (`creator_id`),
  KEY `dvadmin_system_users_current_role_id_56ce41ce` (`current_role_id`),
  KEY `dvadmin_system_users_dept_id_b56f71f6` (`dept_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users`
--

LOCK TABLES `dvadmin_system_users` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users` DISABLE KEYS */;
INSERT INTO `dvadmin_system_users` VALUES ('pbkdf2_sha256$600000$REPLACE_ME_SALT$REPLACE_ME_HASH','2026-08-31 18:41:49.716490',1,'','',1,1,'2026-08-27 18:04:38.898749',1,NULL,NULL,NULL,'2026-09-01 08:25:03.103837','2026-08-27 18:04:38.898905','superadmin','dvadmin@django-vue-admin.com','13333333333',NULL,'超级管理员',1,0,0,1,'zh-cn',NULL,3,1),('pbkdf2_sha256$600000$REPLACE_ME_SALT$REPLACE_ME_HASH',NULL,0,'','',1,1,'2026-08-27 18:04:38.911341',2,NULL,NULL,NULL,'2026-08-27 18:04:38.918671','2026-08-27 18:04:38.911459','admin','dvadmin@django-vue-admin.com','18888888888','','管理员',1,0,0,0,'zh-cn',NULL,NULL,1),('pbkdf2_sha256$600000$REPLACE_ME_SALT$REPLACE_ME_HASH',NULL,0,'','',1,1,'2026-08-27 18:04:38.924337',3,NULL,NULL,NULL,'2026-08-27 18:04:38.934548','2026-08-27 18:04:38.924456','test','dvadmin@django-vue-admin.com','18888888888','','测试人员',1,0,0,0,'zh-cn',NULL,NULL,3);
/*!40000 ALTER TABLE `dvadmin_system_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users_groups`
--

DROP TABLE IF EXISTS `dvadmin_system_users_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `users_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_users_groups_users_id_group_id_7460f482_uniq` (`users_id`,`group_id`),
  KEY `dvadmin_system_users_groups_group_id_42e8a6dc_fk_auth_group_id` (`group_id`),
  CONSTRAINT `dvadmin_system_users_groups_group_id_42e8a6dc_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `dvadmin_system_users_users_id_f20fa5bc_fk_dvadmin_s` FOREIGN KEY (`users_id`) REFERENCES `dvadmin_system_users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users_groups`
--

LOCK TABLES `dvadmin_system_users_groups` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_users_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users_manage_dept`
--

DROP TABLE IF EXISTS `dvadmin_system_users_manage_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users_manage_dept` (
  `id` int NOT NULL AUTO_INCREMENT,
  `users_id` bigint NOT NULL,
  `dept_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_users_manage_dept_users_id_dept_id_17a55f94_uniq` (`users_id`,`dept_id`),
  KEY `dvadmin_system_users_manage_dept_users_id_ae9842ec` (`users_id`),
  KEY `dvadmin_system_users_manage_dept_dept_id_7c352d4a` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users_manage_dept`
--

LOCK TABLES `dvadmin_system_users_manage_dept` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users_manage_dept` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_users_manage_dept` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users_post`
--

DROP TABLE IF EXISTS `dvadmin_system_users_post`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users_post` (
  `id` int NOT NULL AUTO_INCREMENT,
  `users_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_users_post_users_id_post_id_41f83b22_uniq` (`users_id`,`post_id`),
  KEY `dvadmin_system_users_post_users_id_8ab2e760` (`users_id`),
  KEY `dvadmin_system_users_post_post_id_50054985` (`post_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users_post`
--

LOCK TABLES `dvadmin_system_users_post` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users_post` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_users_post` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users_role`
--

DROP TABLE IF EXISTS `dvadmin_system_users_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users_role` (
  `id` int NOT NULL AUTO_INCREMENT,
  `users_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_users_role_users_id_role_id_02908e92_uniq` (`users_id`,`role_id`),
  KEY `dvadmin_system_users_role_users_id_a25207bc` (`users_id`),
  KEY `dvadmin_system_users_role_role_id_e37d9591` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users_role`
--

LOCK TABLES `dvadmin_system_users_role` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users_role` DISABLE KEYS */;
INSERT INTO `dvadmin_system_users_role` VALUES (1,1,1),(3,1,3),(2,3,2);
/*!40000 ALTER TABLE `dvadmin_system_users_role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dvadmin_system_users_user_permissions`
--

DROP TABLE IF EXISTS `dvadmin_system_users_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dvadmin_system_users_user_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `users_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dvadmin_system_users_use_users_id_permission_id_24cd72ef_uniq` (`users_id`,`permission_id`),
  KEY `dvadmin_system_users_permission_id_c8ec58dc_fk_auth_perm` (`permission_id`),
  CONSTRAINT `dvadmin_system_users_permission_id_c8ec58dc_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `dvadmin_system_users_users_id_fd3b0217_fk_dvadmin_s` FOREIGN KEY (`users_id`) REFERENCES `dvadmin_system_users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dvadmin_system_users_user_permissions`
--

LOCK TABLES `dvadmin_system_users_user_permissions` WRITE;
/*!40000 ALTER TABLE `dvadmin_system_users_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `dvadmin_system_users_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `monitor_prometheus_source`
--

DROP TABLE IF EXISTS `monitor_prometheus_source`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `monitor_prometheus_source` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  `modifier` varchar(255) DEFAULT NULL,
  `dept_belong_id` varchar(255) DEFAULT NULL,
  `update_datetime` datetime(6) DEFAULT NULL,
  `create_datetime` datetime(6) DEFAULT NULL,
  `name` varchar(64) NOT NULL,
  `url` varchar(255) NOT NULL,
  `status` int NOT NULL,
  `sort` int DEFAULT NULL,
  `creator_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `monitor_prometheus_source_creator_id_3578c1de` (`creator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `monitor_prometheus_source`
--

LOCK TABLES `monitor_prometheus_source` WRITE;
/*!40000 ALTER TABLE `monitor_prometheus_source` DISABLE KEYS */;
INSERT INTO `monitor_prometheus_source` VALUES (1,NULL,'1',NULL,'2026-08-28 16:55:26.516454','2026-08-28 16:40:38.268092','本机 Prometheus','http://172.30.0.16:9090',1,1,NULL);
/*!40000 ALTER TABLE `monitor_prometheus_source` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'django-vue3-admin'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-01  9:08:00
