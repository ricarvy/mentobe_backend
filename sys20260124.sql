-- MySQL dump 10.13  Distrib 8.0.44, for macos15 (x86_64)
--
-- Host: 127.0.0.1    Database: mentobe
-- ------------------------------------------------------
-- Server version	8.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin_users`
--

DROP TABLE IF EXISTS `admin_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_users` (
  `id` char(36) NOT NULL,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) DEFAULT 'admin',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_users`
--

LOCK TABLES `admin_users` WRITE;
/*!40000 ALTER TABLE `admin_users` DISABLE KEYS */;
INSERT INTO `admin_users` VALUES ('b0f3b97b-22e9-478d-8da9-44d531cb135b','admin','$2b$12$3WMa.m78maDtq8ML6Aijje03pbhf2hLQbbzbhgVinUhZngANNOQP6','admin','2026-01-24 06:20:57');
/*!40000 ALTER TABLE `admin_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_quotas`
--

DROP TABLE IF EXISTS `daily_quotas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_quotas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` char(36) DEFAULT NULL,
  `date` date NOT NULL,
  `count` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `daily_quotas_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_quotas`
--

LOCK TABLES `daily_quotas` WRITE;
/*!40000 ALTER TABLE `daily_quotas` DISABLE KEYS */;
INSERT INTO `daily_quotas` VALUES (1,'66e0da93-a62e-45a5-a7c9-506fd19118fc','2026-01-24',2,'2026-01-24 05:54:46');
/*!40000 ALTER TABLE `daily_quotas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payments`
--

DROP TABLE IF EXISTS `payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` char(36) DEFAULT NULL,
  `stripe_session_id` varchar(255) DEFAULT NULL,
  `amount_total` int DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `price_id` varchar(255) DEFAULT NULL,
  `vip_level` int DEFAULT NULL,
  `vip_duration` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payments`
--

LOCK TABLES `payments` WRITE;
/*!40000 ALTER TABLE `payments` DISABLE KEYS */;
INSERT INTO `payments` VALUES (1,'00000000-0000-0000-0000-000000000000','cs_test_simulated_1769233018',499,'usd','paid','price_1Sren7GVP93aj81Tr4d18z2S',1,'monthly','2026-01-24 05:36:58'),(2,'66e0da93-a62e-45a5-a7c9-506fd19118fc','cs_test_123',1000,'usd','paid','price_pro_monthly',1,'monthly','2026-01-24 08:10:36'),(3,'66e0da93-a62e-45a5-a7c9-506fd19118fc','cs_test_123',1000,'usd','paid','price_pro_monthly',1,'monthly','2026-01-24 08:10:53');
/*!40000 ALTER TABLE `payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tarot_interpretations`
--

DROP TABLE IF EXISTS `tarot_interpretations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tarot_interpretations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` char(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `question` mediumtext COLLATE utf8mb4_unicode_ci,
  `spread_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cards` json DEFAULT NULL,
  `interpretation` mediumtext COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `tarot_interpretations_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tarot_interpretations`
--

LOCK TABLES `tarot_interpretations` WRITE;
/*!40000 ALTER TABLE `tarot_interpretations` DISABLE KEYS */;
INSERT INTO `tarot_interpretations` VALUES (2,'66e0da93-a62e-45a5-a7c9-506fd19118fc','What is my career outlook?','single','[{\"id\": 0, \"name\": \"The Fool\", \"suit\": null, \"image\": null, \"nameEn\": null, \"nameJa\": null, \"number\": null, \"meaning\": null, \"imageUrl\": null, \"keywords\": null, \"isReversed\": false, \"reversedMeaning\": null}]','### ? 整体氛围  \n愚人牌（The Fool）带来的是一种轻盈而充满希望的能量，仿佛站在人生的悬崖边却选择张开双臂——职业生涯即将迎来充满可能性的新篇章，但这冒险之旅需要以信任与勇气为基石，而非盲目冲动。\n\n\n### ? 牌面深度解析  \n**愚人（正位）**  \n愚人在职业场域中，是一个充满象征意义的“冒险者”符号。正位时，它代表**无畏的新起点**：你可能即将迎来一个全新的职业机会（如创业、转行、接手新项目），或是在现有岗位上获得突破性的发展机遇。这张牌强调“带着天真的热情，勇敢踏入未知”——它并非鼓励鲁莽行事，而是暗示你需要**放下对“失败”的恐惧**，相信自己的直觉与内在驱动力，以开放心态拥抱变化。  \n\n愚人牌的“未知”并非危险，而是**创新的土壤**：你或许正处于职业瓶颈期，或是对现状感到倦怠，此时它提示你：跳出固有的思维框架，允许自己“从零开始”，哪怕前路看起来模糊不清，也能凭借纯粹的行动力开辟新路径。这张牌也在提醒你：不要被过去的经验束缚，偶尔的“天真”（即放下过度思虑）反而能让你发现他人忽略的机遇。\n\n\n### ? 指引与建议  \n面对即将展开的职业前景，愚人牌传递的核心启示是：**以勇气为帆，以信任为舵**。  \n\n- **主动迎接“不确定性”**：若有新的工作方向或项目邀请，不妨带着“试试看”的开放心态参与，不必因“未知”而犹豫——正是这种“无畏”能让你突破舒适区，获得意想不到的成长。  \n- **轻装上阵，拒绝“过度规划”**：虽然冒险需要智慧，但愚人牌的“天真”并非否定准备，而是建议你：在行动前做好基础规划（如技能储备、风险预判），但不要让细节恐惧淹没初心。  \n- **允许自己“笨拙地成长”**：职业初期的“跌跌撞撞”是必然的，但愚人牌暗示“错误是探索的一部分”。不必因暂时的迷茫或失误否定自己，反而要相信“每一步都是经验的积累”。  \n\n最后，愿你带着愚人般的纯粹热情，在职业的未知旅程中，既勇敢迈步，又温柔守护每一个可能性的种子?。','2026-01-24 07:29:18'),(3,'66e0da93-a62e-45a5-a7c9-506fd19118fc','我的未来事业如何发展？','single','[{\"id\": 22, \"name\": \"权杖王牌\", \"suit\": \"Wands\", \"image\": \"/tarot-cards/result/Minor/Ace_of_Wands_Creativity.png\", \"nameEn\": \"Ace of Wands\", \"nameJa\": \"ワンドのエース\", \"number\": 1, \"meaning\": \"新的开始、灵感、行动、激情、创造力\", \"imageUrl\": \"/tarot-cards/result/Minor/Ace_of_Wands_Creativity.png\", \"keywords\": [\"new beginnings\", \"inspiration\", \"action\", \"passion\", \"creativity\"], \"isReversed\": false, \"reversedMeaning\": \"延迟、缺乏方向、缺乏激情\"}]','### ? **整体氛围**  \n这张牌带来的能量充满了**行动的火焰**与**新生的光芒**，仿佛事业正站在一个充满可能性的起点，每一个细胞都跃跃欲试，准备迎接全新的挑战与机遇。权杖王牌的正位如同清晨破晓的第一缕阳光，驱散迷茫，点燃你对事业的全部热忱。\n\n\n### ? 牌面深度解析  \n**1. 现状 - 权杖王牌 (正位)**  \n作为“现状”的权杖王牌正位，它揭示了你当前事业状态的核心特质——**你正站在一个充满活力的新起点上**。  \n\n“新的开始”在这里并非指过去的结束，而是你内心对事业的重新定义或外部机遇的主动承接：或许是一个搁置已久的创意项目终于被重新拾起，或许是一份能点燃你热情的新工作邀约，又或是你在现有领域找到了突破性的方向。“灵感”与“创造力”是这张牌的灵魂，它暗示你近期正被某种强烈的直觉或独特视角驱动，对未来的职业蓝图有了清晰的轮廓。  \n\n更重要的是“行动”与“激情”的能量：你并非停留在空想，而是内心涌动着将想法落地的冲动，身体里仿佛有股“不做就会遗憾”的紧迫感。这份正位的权杖，让你此刻的事业状态充满了**主动出击的勇气**与**一往无前的决心**，没有犹豫，只有“立刻行动”的冲动。\n\n\n### ? 指引与建议  \n既然权杖王牌的能量是“动”与“新”，请**立刻抓住这股势头**——不要让灵感在犹豫中冷却，不要让热情在等待中消磨。  \n\n将你脑海中的“新想法”拆解为可执行的小目标：哪怕只是今天列出一份初步计划，明天约见一位潜在的合作伙伴，或是下周投入30%的精力尝试一个新的业务方向，都是在为未来的事业大厦打下基石。记住，权杖王牌的“激情”并非盲目冲动，而是**带着创造力的精准行动**——你需要将这份热情与理性结合，让灵感成为“解决问题”的钥匙，而非“空想的碎片”。  \n\n**关键建议**：允许自己“试错”，权杖王牌的正位天然带着“不怕犯错”的底气，你的每一次小尝试都是在为未来的成功积累经验。同时，保持对事业的热爱与好奇心，这会是你持续前进的燃料。  \n\n\n? 未来的事业之路，正因你此刻的行动力而铺展成一条充满光芒的大道。勇敢去闯，让你的热情与创意成为事业的“权杖”，引领你走向更高的山峰。','2026-01-24 10:46:24');
/*!40000 ALTER TABLE `tarot_interpretations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` char(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `username` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `quota` int DEFAULT '3',
  `vip_level` int DEFAULT '0',
  `vip_expire_at` datetime DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES ('00000000-0000-0000-0000-000000000000','demo@mentobai.com','Demo User','$2b$12$ugwpP5n9Ws2ORPDVAWD.vuTfZhMv1qwdVDgJ364s9M3c33cgr7rmO',1,999999,1,'2026-02-23 05:36:58','2026-01-24 05:36:58'),('607160a9-64ec-4e58-8d9f-e887cd889f32','user@example.com','user','$2b$12$QGolQueE4mhJx1Fv3OPAWegmfukiflToACGwJ/mrza4O8ZUeSOw2u',1,3,0,NULL,'2026-01-24 11:04:44'),('66e0da93-a62e-45a5-a7c9-506fd19118fc','597928240@qq.com','597928240','$2b$12$yo51P8kZkhQERr9haL510uvc7tCSg5aTJeE9RYQR4ICpvyFrGqsPS',1,999998,0,NULL,'2026-01-24 05:43:06');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-24 19:30:40
